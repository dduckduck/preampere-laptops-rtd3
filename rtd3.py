import os
import argparse
from typing import Callable, Any

# =========================================================
# Section: Config files
# =========================================================

NVIDIA_GPUS_PATH = "/proc/driver/nvidia/gpus/"
BATTS_PATH = "/sys/class/power_supply/"
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
    "udev": {  # Requires root access
        "path": [
            "/etc/udev/rules.d/80-nvidia-pm.rules",
            "/lib/udev/rules.d/80-nvidia-pm.rules"
        ],
        "value": """# Enable runtime PM for NVIDIA VGA/3D controller devices on driver bind
ACTION=="bind", SUBSYSTEM=="pci", ATTR{vendor}=="0x10de", ATTR{class}=="0x030000", TEST=="power/control", ATTR{power/control}="auto"
ACTION=="bind", SUBSYSTEM=="pci", ATTR{vendor}=="0x10de", ATTR{class}=="0x030200", TEST=="power/control", ATTR{power/control}="auto"

# Disable runtime PM for NVIDIA VGA/3D controller devices on driver unbind
ACTION=="unbind", SUBSYSTEM=="pci", ATTR{vendor}=="0x10de", ATTR{class}=="0x030000", TEST=="power/control", ATTR{power/control}="on"
ACTION=="unbind", SUBSYSTEM=="pci", ATTR{vendor}=="0x10de", ATTR{class}=="0x030200", TEST=="power/control", ATTR{power/control}="on"
"""},
    "modprobe": {  # Requires root access
        "path": [
            "/etc/modprobe.d/nvidia-pm.conf",
            "/etc/modprobe.d/nvidia.conf"
        ],
        "value": """options nvidia NVreg_DynamicPowerManagement=0x0{}
options nvidia NVreg_EnableGpuFirmware={}
"""
    }
}


NVIDIA_FUNCTION = {
    "0": "VGA controller/3D controller",
    "1": "Audio device",
    "2": "USB xHCI Host controller",
    "3": "USB Type-c UCSI controller"
}


VERIFY_HANDLERS: dict[str, Callable[[str], dict[str, Any]]] = {}
STATE_HANDLERS: dict[str, Callable[[str], dict[str, Any]]] = {}

# =========================================================
# Section: Basic operations
# =========================================================


def _read_file(path: str, mode: str = 'r') -> str:
    data = ""
    try:
        with open(path, mode) as f:
            if mode == "rb":
                data = f.read().decode(errors="ignore")
            else:
                data = f.read()
    except Exception as e:
        print(f"Could not read {path} {str(e)}")
    return data


def _list_dir(path: str) -> list:
    output = []
    try:
        output = os.listdir(path)
    except Exception as e:
        print(f"Could not list {path} {str(e)}")
    return output


def _find_file(paths: list) -> str:
    output = ""
    try:
        for path in paths:
            if os.path.exists(path):
                output = path
                break
    except Exception as e:
        print(f"Could not find path :{str(e)}")
    return output


def _create_file(path: str, data: str, force: bool = False):
    print(f"Creating: {path}")
    try:
        if os.path.exists(path):
            print(f"{path} already exists. Creating backup...")
            backup_path = f"{path}.bak"
            if os.path.exists(backup_path):
                if not force:
                    print(
                        "Backup already exists. The operation is canceled. Use --force to overwrite.")
                    return
                else:
                    print(
                        "--force is issued. The file will be overwritten and no backup will be created")
                    pass
            else:
                print(f"Crearing backup")
                os.rename(path, backup_path)
                print(f"Backup created at {backup_path}")

        if not os.path.exists(os.path.dirname(path)):
            print(f"Creating new file {path}")
            os.makedirs(os.path.dirname(path))

        with open(path, 'w') as f:
            print(f"Writing data to : {path}")
            f.write(data)
        print(f"Successfully installed {path}")
    except Exception as e:
        print(f"Could not finish the installation {str(e)}")


def _delete_file(file: str) -> None:
    print(f"Deleting {file}")
    for path in NVIDIA_FILES[file]["path"]:
        if os.path.exists(path):
            print(f"Removing: {path}")
            os.remove(path)
        if os.path.exists(path + ".bak"):
            print(f"Restoring backup: {path}.bak -> {path}")
            os.rename(path + ".bak", path)
    print("Uninstallation process completed.")


def handler(dict_handler: dict[str, Callable[[str], dict[str, Any]]], name: str):
    def decorator(func: Callable[[str], dict[str, Any]]):
        dict_handler[name] = func
        return func
    return decorator

# =========================================================
# Section: --verify Handlers
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
    supported = "10" == data
    return {"value": data, "supported": str(supported)}


@handler(VERIFY_HANDLERS, "s3")
def s3_handler(data: str) -> dict[str, Any]:
    data = data.strip()
    supported = "deep" in data
    return {"value": data, "supported": str(supported)}


# =========================================================
# Section: --state Handlers
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
        print(e)
    return {"value": value}


@handler(STATE_HANDLERS, "energy_now")
def energy_now_handler(data: str) -> dict[str, Any]:
    try:
        value = int(data.strip())
        value *= (10**-6)
    except ValueError as e:
        print(e)
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

    gpus_dirs = _list_dir(NVIDIA_GPUS_PATH)
    for pci in gpus_dirs:
        data = pci_handler(pci)
        for key, value in data.items():
            rows.append([key, value])
        for key, value in NVIDIA_STATE.items():
            raw = _read_file(value.format(pci))
            data = STATE_HANDLERS[key](raw)
            rows.append([key]+[value for key, value in data.items()])
        rows.append(['-'*5, '-'*5])
    batts = _list_dir(BATTS_PATH)
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


def install(power_mode: int, enable_firmware: int, force: bool) -> None:
    print("Starting installation")
    udev_path = _find_file(NVIDIA_FILES["udev"]["path"])
    udev_path = udev_path if udev_path else NVIDIA_FILES["udev"]["path"][0]
    udev_data = NVIDIA_FILES["udev"]["value"]
    _create_file(udev_path, udev_data, force)

    modprobe_path = _find_file(NVIDIA_FILES["modprobe"]["path"])
    modprobe_path = modprobe_path if modprobe_path else NVIDIA_FILES["modprobe"]["path"][0]
    modprobe_data = NVIDIA_FILES["modprobe"]["value"].format(
        power_mode, enable_firmware)
    _create_file(modprobe_path, modprobe_data, force)


def uninstall() -> None:
    _delete_file("udev")
    _delete_file("modprobe")

# =========================================================
# Section: Main and arguments
# =========================================================


def setup_args() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="RTD3 Tool: A utility for managing and diagnosing NVIDIA GPU power management on hybrid laptops.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_info = subparsers.add_parser("info", help="Shows info")
    parser_info.add_argument("-v", "--verify", action="store_true",
                             help="Verifies system requirements as specified in nvidia docs.")
    parser_info.add_argument("-s", "--state", action="store_true",
                             help="Show the current status of the dGPU, battery and indicate if the udev and modprobe files are present.\
                             If more than one dgpu or battery available, individual information for each device will be shown")

    parser_install = subparsers.add_parser(
        "install", help="install udev and modprobe files. if these files already exist, a backup will be created.\
                        (If a backup exists, the installation wont be completed).")
    parser_install.add_argument(
        "-p", "--powermode", type=int, choices=[0, 1, 2], default=2,
        help=(
            "Configure NVIDIA dynamic power management (NVreg_DynamicPowerManagement): \
            0 - disables D3 power management, 1 - enables coarse-grained power control, 2 - enable fine-grained power control.\
            Default value is 2."
        )
    )
    parser_install.add_argument("-e", "--enablefirmware", type=int, choices=[0, 1], default=0,
                                help="Enables (1) or disables (0) GpuFirmware. Only works on the closed source driver. Default 0.")
    parser_install.add_argument("-f", "--force", action="store_true", default=False,
                                help="When this flag is enabled, the udev and modprobe files will be overwritten without creatng a backup. Proceed with caution.")

    parser_uninstall = subparsers.add_parser(
        "uninstall", help="Deletes udev and modprobe files. If backups are available, the original content will be restored.")
    return parser


def main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    match(args.command):
        case "info":
            if args.verify:
                verify()
            elif args.state:
                state()
            else:
                parser_info = parser.parse_args(["info", "--help"])
                parser.print_help()
        case "install":
            install(args.powermode, args.enablefirmware, args.force)
        case "uninstall":
            uninstall()
        case _:
            parser.print_help()


if __name__ == "__main__":
    parser = setup_args()
    main(parser)
