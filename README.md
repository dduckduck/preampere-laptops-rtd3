Thi project is presented as is.

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
to do

