import os
import argparse
from typing import Callable, Any

# =========================================================
# Section: Configs
# =========================================================


VERIFY_HANDLERS: dict[str, Callable[[str], dict[str, Any]]] = {}
STATE_HANDLERS: dict[str, Callable[[str], dict[str, Any]]] = {}
NVIDIA_GPUS_PATH = "/proc/driver/nvidia/gpus/"
BATTS_PATH = "/sys/class/power_supply/"
NOTEBOOK_CHASSIS = ["8", "9", "10", "14"]
NVIDIA_FUNCTION = {
    "0": "VGA controller/3D controller",
    "1": "Audio device",
    "2": "USB xHCI Host controller",
    "3": "USB Type-c UCSI controller"
}


SYS_FILES = {
    "chassis": {
        "path": "/sys/class/dmi/id/chassis_type",
        "mode": 'r'
    },
    "acpi": {
        "path": "/sys/firmware/acpi/tables/DSDT", "mode": 'rb'
    },
    "kernel": {
        "path": "/proc/version",
        "mode": 'r'
    },
    "s3": {
        "path": "/sys/power/mem_sleep",
        "mode": 'r'
    }
}


NVIDIA_STATE = {
    "rtd3_status": "/proc/driver/nvidia/gpus/{}/power",
    "power_state": "/sys/bus/pci/devices/{}/power_state",
    "runtime_status": "/sys/bus/pci/devices/{}/power/runtime_status"
}


BATTS_STATE = {
    "power_now": "/sys/class/power_supply/{}/power_now",
    "energy_now": "/sys/class/power_supply/{}/energy_now",
}


NVIDIA_FILES = {
    "udev": {
        "src": "80-nvidia-pm.rules",
        "dst": "/etc/udev/rules.d/"
    },
    "modprobe": {
        "src": "nvidia-pm.conf",
        "dst": "/etc/modprobe.d/"
    }
}


# =========================================================
# Section: Basic operations
# =========================================================


def _create_file(file: str):
    print(f"Creating {file}")
    src = NVIDIA_FILES[file]["src"]
    dst = NVIDIA_FILES[file]["dst"]
    with open(src, 'r') as f:
        with open(os.path.join(dst, src), 'w') as dst_f:
            dst_f.write(f.read())
    print(f"Created {file}")


def _delete_file(path: str):
    print(f"Deleting: {path}")
    os.remove(path)
    print(f"Deleted: {path}")


def _read_file(path: str, mode: str = 'r') -> str:
    data = ""
    with open(path, mode) as f:
        data = f.read().decode(errors="ignore") if mode == "rb" else f.read()
    return data


# =========================================================
# Section: Handlers
# =========================================================


def handler(dict_handler: dict[str, Callable[[str], dict[str, Any]]], name: str):
    def decorator(func: Callable[[str], dict[str, Any]]):
        dict_handler[name] = func
        return func
    return decorator

# =========================================================
# Section: info --verify Handlers
# =========================================================


@handler(VERIFY_HANDLERS, "kernel")
def kernel_handler(data: str) -> dict[str, Any]:
    parts = data.split()
    version_str = parts[2] if len(parts) > 2 else "Unknown"
    version_parts = version_str.split('.')
    first, second = -1, -1
    try:
        if len(version_parts) >= 2:
            first, second = map(int, version_parts[:2])
    except ValueError:
        first, second = -1, -1
    supported = (first, second) >= (4, 18)
    return {
        "value": f"{first}.{second}",
        "supported": str(supported)
    }


@handler(VERIFY_HANDLERS, "acpi")
def acpi_handler(data: str) -> dict[str, Any]:
    flags = ["_PR0", "_PR3"]
    value = ""
    for flag in flags:
        if flag in data:
            value += flag
    supported = "_PR0" in value and "_PR3" in value
    return {
        "value": value,
        "supported": str(supported)
    }


@handler(VERIFY_HANDLERS, "chassis")
def chassis_handler(data: str) -> dict[str, Any]:
    data = data.strip()
    supported = data in NOTEBOOK_CHASSIS
    return {"value": data, "supported": str(supported)}


@handler(VERIFY_HANDLERS, "s3")
def s3_handler(data: str) -> dict[str, Any]:
    data = data.strip()
    supported = "deep" in data
    return {"value": data, "supported": str(supported)}


# =========================================================
# Section: info --state Handlers
# =========================================================

@handler(STATE_HANDLERS, "rtd3_status")
def rtd3_handler(data: str) -> dict[str, Any]:
    temp = data.splitlines()
    temp = temp[0].split(':') if len(temp) > 1 else temp
    value = temp[1].strip() if len(temp) > 1 else "Unknown"
    return {"value": value}


@handler(STATE_HANDLERS, "power_state")
def power_state_handler(data: str) -> dict[str, Any]:
    return {"value": data.strip()}


@handler(STATE_HANDLERS, "runtime_status")
def runtime_status_handler(data: str) -> dict[str, Any]:
    return {"value": data.strip()}


@handler(STATE_HANDLERS, "power_now")
def power_now_handler(data: str) -> dict[str, Any]:
    value = -1
    try:
        value = int(data.strip())
        value *= (10**-6)
    except ValueError as e:
        print(str(e))
    return {"value": value}


@handler(STATE_HANDLERS, "energy_now")
def energy_now_handler(data: str) -> dict[str, Any]:
    value = -1
    try:
        value = int(data.strip())
        value *= (10**-6)
    except ValueError as e:
        print(str(e))
    return {"value": value}


@handler(STATE_HANDLERS, "pci_info")
def pci_handler(data: str) -> dict[str, Any]:
    lines = data.strip().split(':')
    domain = bus = device = function = -1
    if len(lines) > 2:
        domain = lines[0]
        bus = lines[1]
        device = lines[2]
        temp = device.split('.')
        if len(temp) > 1:
            device = temp[0]
            function = NVIDIA_FUNCTION[temp[1]]
    return {"domain": domain, "bus": bus, "device": device, "function": function}

# =========================================================
# Section: Utilities
# =========================================================


def _print_table(headers: list[str], rows: list[list[str]], margin: int = 2, name="Table") -> None:
    col_width = max([len(str(val)) for val in headers] + [len(str(val))
                    for row in rows for val in row]) + margin
    table_width = col_width * len(headers)
    print(name.center(table_width, '='))
    header = "".join(f"{header:<{col_width}}" for header in headers)
    print(header)
    print('-' * table_width)
    for row in rows:
        row_str = "".join(f"{val:<{col_width}}" for val in row)
        print(row_str)
    print('=' * table_width)


# =========================================================
# Section: Commands
# =========================================================


def verify() -> dict:
    headers = ["Check", "Value", "Supported"]
    rows = []
    for key, value in SYS_FILES.items():
        raw = _read_file(value["path"], value["mode"])
        data = VERIFY_HANDLERS[key](raw)
        rows.append([key]+[value for key, value in data.items()])
    _print_table(headers, rows, name="Requirements")


def state() -> dict:
    headers = ["key", "value"]
    rows = []
    gpus_dirs = os.listdir(NVIDIA_GPUS_PATH)
    for pci in gpus_dirs:
        data = pci_handler(pci)
        for key, value in data.items():
            rows.append([key, value])
        for key, value in NVIDIA_STATE.items():
            raw = _read_file(value.format(pci))
            data = STATE_HANDLERS[key](raw)
            rows.append([key]+[value for key, value in data.items()])
        rows.append(['-'*5, '-'*5])
    batts = os.listdir(BATTS_PATH)
    for batt in [batt for batt in batts if "BAT" in batt]:
        rows.append(["battery", batt])
        temp = []
        for key, value in BATTS_STATE.items():
            raw = _read_file(value.format(batt))
            data = STATE_HANDLERS[key](raw)
            temp.append(data["value"])
            rows.append([key]+[value for key, value in data.items()])
        rows.append(["Remaining time", temp[1] /
                    temp[0] if len(temp) > 1 and temp[0] != 0 else -1])
        rows.append(['-'*5, '-'*5])
    _print_table(headers, rows, name="State")


def install() -> None:
    print("=== Installation started ===")
    print("Copying udev file...")
    _create_file("udev")
    print("Udev file installed successfully.")
    print("Copying modprobe file...")
    _create_file("modprobe")
    print("Modprobe file installed successfully.")
    print("=== Installation finished ===")


def uninstall() -> None:
    print("=== Uninstallation started ===")
    udev_path = os.path.join(
        NVIDIA_FILES["udev"]["dst"], NVIDIA_FILES["udev"]["src"])
    modprobe_path = os.path.join(
        NVIDIA_FILES["modprobe"]["dst"], NVIDIA_FILES["modprobe"]["src"])
    print(f"Deleting file: {udev_path}")
    _delete_file(udev_path)
    print("Udev file deleted successfully.")
    print(f"Deleting file: {modprobe_path}")
    _delete_file(modprobe_path)
    print("Modprobe file deleted successfully.")
    print("=== Uninstallation finished ===")


# =========================================================
# Section: Main and arguments
# =========================================================


def setup_args() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="RTD3 Tool: A utility for managing and diagnosing NVIDIA GPU power management on hybrid laptops."
    )
    parser.add_argument("-v", "--verify", action="store_true",
                        help="Verifies system requirements as specified in NVIDIA docs.")
    parser.add_argument("-s", "--state", action="store_true",
                        help="Shows the current status of the dGPU and battery.")
    parser.add_argument("-i", "--install", action="store_true",
                        help="Installs required udev and modprobe files.")
    parser.add_argument("-u", "--uninstall", action="store_true",
                        help="Removes udev and modprobe files.")
    return parser


def main():
    parser = setup_args()
    args = parser.parse_args()

    if args.verify:
        verify()
    elif args.state:
        state()
    elif args.install:
        install()
    elif args.uninstall:
        uninstall()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
