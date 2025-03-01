import os
import argparse
from typing import Callable, Any

# =========================================================
# Section: Config files
# =========================================================

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

DGPU_FILES = {
    "gpus": "/proc/driver/nvidia/gpus/",
    #    "model": "/proc/driver/nvidia/gpus/{}/information",
    "rtd3_status": "/proc/driver/nvidia/gpus/{}/power",
    "power_state": "/sys/bus/pci/devices/{}/power_state",
    "runtime_status": "/sys/bus/pci/devices/{}/power/runtime_status"
}


BAT_FILES = {
    "power_supply": "/sys/class/power_supply/",
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
    0: "VGA controller/3D controller",
    1: "Audio device",
    2: "USB xHCI Host controller",
    3: "USB Type-c UCSI controller"
}


DATA_HANDLERS: dict[str, Callable[[str], dict[str, Any]]] = {}


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


def _extract_data(value: str, data: str) -> str:
    output = ""
    match value:
        case "kernel":
            temp = data.strip().split()
            output = temp[2] if len(temp) >= 3 else "Unknown"
        case "chassis":
            output = data.strip()
        case "acpi":
            output = ", ".join(tag for tag in ["_PR0", "_PR3"] if tag in data)
        case "s3":
            output = "deep" if "deep" in data else "None"
        case "rtd3_status":
            temp = data.splitlines()[0]
            if "Runtime D3 status" in temp:
                output = temp.split(':', 1)[1].strip()
        case "power_state":
            output = data.strip()
        case "runtime_status":
            output = data.strip()
        case "power_now":
            output = int(data.strip())
        case "energy_now":
            output = int(data)
    return output


def _validate(value: str, data: str) -> bool:
    output = False
    match value:
        case "kernel":
            nums = data.split('.')
            first, second = -1, -1
            if nums and len(nums) >= 2:
                first, second = (map(int, nums[:2]))
            output = (first, second) >= (4, 18)
        case "chassis":
            output = ("10" == data)
        case "acpi":
            output = ("_PR0" in data and "_PR3" in data)
        case "s3":
            output = "deep" in data
        case "udev":
            output = NVIDIA_FILES["udev"]["value"] in data
    return output


def _power_watts(value: str) -> int:
    power_draw = -1
    try:
        power_draw = int(value)
    except Exception as e:
        print(f"Clould not obtain power draw {str(e)}")
    return power_draw*(10**-6)


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


# =========================================================
# Section: Handlers
# =========================================================

def reg_handler(name: str):
    def decorator(func: Callable[[str], dict[str, Any]]):
        DATA_HANDLERS[name] = func
        return func
    return decorator


@ reg_handler("kernel")
def kernel_handler(data: str) -> dict[str, Any]:
    output = "Unknown"
    return output


@ reg_handler("acpi")
def acpi_handler(data: str) -> dict[str, Any]:
    output = "Unknown"
    return output


@ reg_handler("chassis")
def chassis_handler(data: str) -> dict[str, Any]:
    output = "Unknown"
    return output


@ reg_handler("s3")
def s3_handler(data: str) -> dict[str, Any]:
    output = "Unknown"
    return output


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


def _gpu_info(pci: str) -> dict:
    pci_info = {"bus": -1, "id": -1, "function": "Unknown"}
    pci_temp = pci.split(':')
    if len(pci_temp) == 3:
        pci_info["bus"] = pci_temp[1]
        temp = pci_temp[2].split('.')
        pci_info["function"] = NVIDIA_FUNCTION[int(temp[1])]
        pci_info["id"] = temp[0]
        for key, value in [(k, v) for (k, v) in DGPU_FILES.items() if k != "gpus"]:
            data = _extract_data(key, _read_file(value.format(pci)))
            pci_info[key] = data
    return pci_info


def _batt_info(batt: str) -> dict:
    batt_info = {"name": batt}
    for key, value in [(k, v) for (k, v) in BAT_FILES.items() if k != "power_supply"]:
        data = _extract_data(key, _read_file(value.format(batt)))
        batt_info[key] = data
    batt_info["rem_time"] = batt_info["energy_now"]/batt_info["power_now"]


# =========================================================
# Section: Commands
# =========================================================


def verify() -> dict:
    headers = ["Check", "Value", "Supported"]
    rows = []
    for key, value in SYS_FILES.items():
        data = DATA_HANDLERS[key]("data")
        print(data)
    _print_table(headers, rows, name="Requirements")


def state() -> dict:
    headers = ["key", "value"]
    rows = []

    gpus_dirs = _list_dir(DGPU_FILES["gpus"])
    for pci in gpus_dirs:
        data = _gpu_info(pci)
        for k, v in data.items():
            rows.append([k, v])
        rows.append(['-'*5, '-'*5])

    batts = [bat for bat in _list_dir(
        BAT_FILES["power_supply"]) if "BAT" in bat]
    for batt in batts:
        path = BAT_FILES["power_now"].format(batt)
        raw_value = _read_file(path)
        power_now = _power_watts(raw_value)
        path = BAT_FILES["energy_now"].format(batt)
        row = [batt, f"{power_now:.2f} W"]
        rows.append(row)
    rows.append(['-'*5, '-'*5])
    for k in NVIDIA_FILES.keys():
        valid_path = _find_file(NVIDIA_FILES[k]["path"])
        row = [k, f"{'Found' if valid_path else 'Not found'}"]
        rows.append(row)
    _print_table(headers, rows, name="Power supply")


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
            Default value is 2. \
            For more information: https://download.nvidia.com/XFree86/Linux-x86_64/565.77/README/dynamicpowermanagement.html"
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
