# Hardware-in-loop
Hardware in loop allows remote code uploading onto STM32 boards without physical presence near the boards.

## Mission
This project uses a Raspberry Pi as a hub to remotely pull code from Git Hub and upload code to the STM32 board. The aim is to facilitate the rapid development of code.

## Requirements
1. An STM32 board
2. A Raspberry Pi
3. Github Actions Runner
This can be set up by going to the settings -> actions -> runner and setting up a Linux runner. Follow all the commands '''**except the last command**''' which executes the `run.sh` shell script. 
4. Libraries
    - Setting up printf and scanf using this [website](https://shawnhymel.com/1873/how-to-use-printf-on-stm32/)
    - Run this sudo command to ensure your system's package list is up to date:
   ```
   sudo apt update
   sudo apt-get update
   ```
    - Install stlink and its dependencies:
    ```
    sudo apt-get install stlink-tools
    ```
    - Install libtool and its dependencies:
   ```
   sudo apt install libtool
   ```
    - Install the ARM GCC toolchain:
   ```
   sudo apt install gcc-arm-none-eabi
   ```
    - Installing OpenOCD using the code below
    ``` 
        git clone git://git.code.sf.net/p/openocd/code
        cd code/
        ./bootstrap
        ./configure
        make
        sudo make install
        cd ..
        rm -rf code/
        sudo nano /etc/udev/rules.d/stlink.rules
    ```
    Now paste this at the end of the file
    ```
    KERNEL=="tty[A-Z]*[0-9]", MODE="0666"
    SUBSYSTEM=="usb", ATTRS{idVendor}=="0483", MODE="0666"
    ```

    Install RPI GPIO library
    ```
    sudo apt-get install python3-rpi.gpio
    ```
   
## Execution
The worklfow on the yaml file starts when a push is made to main. 
Add the `file paths` to the YAML file. These `file paths` are labelled in the `env` section of the YAML file.
To execute this project to the location of the self hosted runner loaction and execute `./run/sh`.

## Precautions
In case the runner is deleted, please go ahead and reinstall the runner at the same location (which by default shall be actions-runner). To do this, **skip** the `first command` (`*mkdir.....*`) . 
If you get an error while configuring, execute
```
ls -a
rm -f .runnner
rm -f config.sh
```

Run tests by doing `python run_test.py my_test_case.json --input-values "override_inputs.json"`



