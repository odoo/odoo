# Creating a Windows EXE Installation Package from setup.nsi

This guide provides step-by-step instructions on how to create Odoo Windows EXE installation package from the `setup.nsi` file using NSIS (Nullsoft Scriptable Install System).

## Prerequisites

### Windows instance
Any Windows system (preferably on a dedicated computer)

### Odoo 
Odoo files should be present on the windows instance.
> [!TIP]
> It does not necessarily need to be installed and setup. You can simply have an uncompressed zip of odoo's GiHhub repository.

Toward this guide, we will call this Odoo content folder `<odoo-folder>`

#### Odoo addons (apps and modules)

Move the modules addons folder that the installer will add to to `<odoo-folder>\odoo\addons`

> [!WARNING]
> If you want to have Odoo standard modules, you will need to move their addons folders from `<odoo-folder>\addons` to `<odoo-folder>\odoo\addons`

> [!NOTE]
> If you want to include enterprise, third party or custom addons you will need to move the addons folders to `<odoo-folder>\addons`


### `NSIS`
1. Download and install NSIS from the official website (https://nsis.sourceforge.io/Download).

2. The following NSIS plugins will also need to be installed:
 - [`AccessControl plug-in`](https://nsis.sourceforge.io/AccessControl_plug-in)
 - [`Inetc plug-in`](https://nsis.sourceforge.io/Inetc_plug-in)
 - [`Nsisunz plug-in`](https://nsis.sourceforge.io/Nsisunz_plug-in)

### Windows executables dependencies

1. Go to `<odoo-folder>\setup\win32\static` create a folder `wkhtmltopdf` 

2. Check the wkhtmltopdf version for your Odoo's version
https://github.com/odoo/odoo/wiki/Wkhtmltopdf

3. Go to the wkhtmltopdf download page and download the appropriate wkhtmltopdf installer executable `wkhtmltox-<wk-version>.msvc<msvc-version>-win64.exe`:
https://github.com/wkhtmltopdf/wkhtmltopdf/releases

4. Run the installer and choose any folder as a temporary folder, let's call it `<tmp-wkhtmltopdf-installation-folder>`

5. From the extracted content, move the `<tmp-wkhtmltopdf-installation-folder>/bin/wkhtmltopdf.exe` file to `<odoo-folder>\setup\win32\static\wkhtmltopdf`


6. Create a folder in `C:` called `odoobuild`

7. In this folder, create the following folders:
- `nssm-2.24` (responsible for handling Odoo as a service)
- `WinPy64` (handle python execution on Windows)
- `vcredist` (contain windows Visual C++ redistributable files required for python)

8. Download the version 2.24 of NSSM:
https://nssm.cc/release/nssm-2.24.zip
Move it's content into the `C:\odoobuild\nssm-2.24` folder

9. Keep only the `win64` folder and content. Other folders and files can be removed

10. Download on WinPython the python version used in `setup.nsi` corresponding to `PYTHONVERSION` (64bit only):
https://github.com/winpython/winpython/releases/download/6.1.20230527/Winpython64-3.10.11.1dot.exe

11. Launching the executable should propose to extract it. Choose `C:\odoobuild\WinPy64` as the extraction folder

> [!WARNING]
> Be aware that the folder should contains the different exe files, **NOT** an extra-folder containing them (`WPy64-310111` for example). You can move the files and folders to the parent folder if it is the case
 
12. Download the latest X64 binary of Microsoft Visual C++ Redistributable: 
https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist 
Move the exectuable file into the `C:\odoobuild\vcredist` folder

> [!WARNING]
> Make sure the executable name is exactly `vc_redist.x64.exe` NOT `VC_redist.x64.exe` rename the file if needed

The final result should look as follows:
```sh
$ tree C:\odoobuild /a /f
```

```
+---nssm-2.24
|   |   
|   \---win64
|           nssm.exe
|           
+---vcredist
|       vc_redist.x64.exe
|       
\---WinPy64
    |   ...
    |
    +---notebooks
    |   ...
    |
    +---python-<python-version>
    |   |   ...
    |   |   python.exe
    |   |   ...
    |   +---DLLs
    |       ...
    |   ...
    |
    \---t
```

### pip libraries dependencies

1. Open the `C:\odoobuild\WinPy64\python-<python-version>` folder. There you should find the file `python.exe`

2. Open the Command Prompt inside the folder and run the following commands individually:
```sh
.\python.exe -m pip install -q --upgrade pip --no-warn-script-location
```

```sh
.\python.exe -m pip install -q -r <odoo-folder>\requirements.txt --no-warn-script-location
```
> [!CAUTION] 
> You might have errors when installating pip libraries,  please make sure that the installation process goes smoothly. Otherwise odoo will not run correctly.

 ```sh
.\python.exe -m pip install -q -r <odoo-folder>\setup\win32\requirements-local-proxy.txt --no-warn-script-location
```

## Compilation

1. Open NSIS software and choose `Compile NSI script`

2. File > Load Script...

3. Navigate to the directory where the `setup.nsi` file is located and choose it

4. Once validated, this should automatically start the compilation

5. Once the compilation process is complete, you will find the generated EXE installation package in the same directory as your setup.nsi file.

6. Test the generated exe installation package on a Windows machine to ensure that it installs Odoo correctly.
