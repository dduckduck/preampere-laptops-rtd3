This project is presented "as is".

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

Additionally, NVIDIA has specific requirements that your system must meet to enable RTD3. Determining if your system is compatible can become a non-trivial process.

## Solution
This tool helps you determine if your system supports RTD3, monitor its current state, and install/uninstall the necessary files to enable RTD3 functionality.

# Requirements
- python >= 3.10
- nvidia propietary driver

# Usage
Three commands are supported at this moment:

- **info**:  
  Verifies if the system requirements are met and provides information about the current state.

- **install**:  
  Installs the udev rule and modprobe parameters.

- **uninstall**:  
  Removes the udev rule and modprobe files.

# Example

## Step 1 (Verifying)
First, check if your system is supported.
(Root permissions are required to read ACPI tables.)




```bash
sudo python rtd3.py info --verify

================================Requirements===============================
Check                    Value                    Supported
---------------------------------------------------------------------------
chassis                  10                       True
acpi                     _PR0, _PR3               True
kernel                   6.12.15-200.fc41.x86_64  True
s3                       deep                     True
===========================================================================
```

If your system is supported, proceed to Step 2.

## Step 2 (Current state)

```bash
python rtd3.py info --state   

===============Power supply===============
key                  value
------------------------------------------
pci                  0000:01:00.0
rtd3_status          Disabled by default
power_state          D0
runtime_status       active
-----                -----
BAT0                 15.94 W
-----                -----
udev                 Found
modprobe             Found
==========================================
```

If `rtd3_status` shows Enabled or `power_state` is D3cold, then you can **stop here**, as your system is running perfectly fine.

## Step 3 (Installing)  
The default options for `modprobe` are:  
- `NVreg_DynamicPowerManagement=0x02`  
- `NVreg_EnableGpuFirmware=0`  

It is assumed that you are using a pre-Ampere GPU. If that is not the case, you should add the following flag to the install command: `--enablefirmware 1`.

You can also specify the power management mode using `--powermode <value>`.

```bash
sudo python rtd3.py install                       

Starting installation
Creating: /etc/udev/rules.d/80-nvidia-pm.rules
Writing data to : /etc/udev/rules.d/80-nvidia-pm.rules
Successfully installed /etc/udev/rules.d/80-nvidia-pm.rules
Creating: /etc/modprobe.d/nvidia-pm.conf
Writing data to : /etc/modprobe.d/nvidia-pm.conf
Successfully installed /etc/modprobe.d/nvidia-pm.conf
```
(Root permissions are required to create udev rule and modprobe.)

Once the installation is complete, you can **reboot**.


## Step 4 (Post installation)

After rebooting, check your system's state again. The expected `rtd3_status` is Enabled.

```bash
python rtd3.py info --state

==================Power supply==================
key                     value
------------------------------------------------
pci                     0000:01:00.0
rtd3_status             Enabled (fine-grained)
power_state             D3cold
runtime_status          suspended
-----                   -----
BAT0                    6.73 W
-----                   -----
udev                    Found
modprobe                Found
================================================
```

(Hey look, the power consumption is reduced by more than half!)


## References
- [NVIDIA Dynamic Power Management](https://download.nvidia.com/XFree86/Linux-x86_64/565.77/README/dynamicpowermanagement.html)  
- [Arch Wiki - PCI-Express Runtime D3 (RTD3) Power Management](https://wiki.archlinux.org/title/PRIME#PCI-Express_Runtime_D3_(RTD3)_Power_Management)
