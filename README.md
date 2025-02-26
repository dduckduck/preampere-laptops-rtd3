This project is presented as is.

# RTD3 Tool

RTD3 Tool is a utility designed to configure RTD3 modes on NVIDIA GPUs prior to the Ampere architecture, providing more efficient power management.

## Why use multiple modes when one will do?

Running a discrete GPU (dGPU) requires additional power, which can significantly reduce battery life.
For users who heavily rely on portability, this extra energy consumption may become a major problem.

As you may know, there are tools that help you switch between integrated and dedicated GPUs. However, 
this process becomes cumbersome as you need to reboot your system every time you make a change.

Stop wasting your time switching between modes and let the NVIDIA driver decide when to power down or activate the dedicated GPU as needed, without manual intervention.

## The Problem
On pre-Ampere models RTD3 feature is disabled by default. To enable it, you need to set the NVIDIA kernel parameter `NVreg_DynamicPowerManagement`. However, on some models, 
enabling dynamic power management completely breaks RTD3. To overcome this issue, you will need to disable the `GpuFirmware` parameter.

Additionally, NVIDIA has specific requirements that your system must meet to enable RTD3. Determining if your system is compatible can be a tedious and non-trivial process.

## Solution
This tool helps you determine if your system supports RTD3, monitor its current state, and install/uninstall the necessary files to enable RTD3 functionality.

# Usage

## General overview
```
usage: rtd3.py [-h] {info,install,uninstall} ...

RTD3 Tool: A utility for managing and diagnosing NVIDIA GPU power management on hybrid laptops.

positional arguments:
  {info,install,uninstall}
    info                Shows info
    install             install udev and modprobe files. if these files already exist, a backup will be
                        created. (If a backup exists, the installation wont be completed).
    uninstall           Deletes udev and modprobe files. If backups are available, the original content
                        will be restored.

```

## Command info

```
usage: rtd3.py info [-h] [-v] [-s]

options:
  -h, --help    show this help message and exit
  -v, --verify  Verifies system requirements as specified in nvidia docs.
  -s, --state   Show the current status of the dGPU, battery and indicate if the udev and modprobe
                files are present. If more than one dgpu or battery available, individual information
                for each device will be shown
```

## Command install

```
usage: rtd3.py install [-h] [-p {0,1,2}] [-e {0,1}] [-f]

options:
  -h, --help            show this help message and exit
  -p, --powermode {0,1,2}
                        Configure NVIDIA dynamic power management (NVreg_DynamicPowerManagement): 0 -
                        disables D3 power management, 1 - enables coarse-grained power control, 2 -
                        enable fine-grained power control. Default value is 2. For more information: ht
                        tps://download.nvidia.com/XFree86/Linux-
                        x86_64/565.77/README/dynamicpowermanagement.html
  -e, --enablefirmware {0,1}
                        Enables (1) or disables (0) GpuFirmware. Only works on the closed source
                        driver. Default 0.
  -f, --force           When this flag is enabled, the udev and modprobe files will be overwritten
                        without creatng a backup. Proceed with caution.
```

## Command uninstall
no arguments required


## Examples
to do
