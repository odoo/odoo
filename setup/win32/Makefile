include Makefile.version
include Makefile.python
include Makefile.servicename

SERVER_DIRECTORY=../..
FILES_DIRECTORY=release

MAKENSIS_ARGUMENTS=/DVERSION=$(VERSION) /DSERVICENAME=${SERVICENAME} /DPYTHONVERSION=${PYTHON_VERSION}

LAUNCH_MAKENSIS=/cygdrive/c/tools/cygwin/makensis $(MAKENSIS_ARGUMENTS) setup.nsi
WINPY32_DIR=/cygdrive/c/odoobuild/WinPy32/python-${PYTHON_VERSION}
WINPY64_DIR=/cygdrive/c/odoobuild/WinPy64/python-${PYTHON_VERSION}.amd64

default: allinone

clean: server_clean
	rm -rf $(FILES_DIRECTORY)/*.exe
	rm -rf *.exe

server_clean:
	rm -rf $(SERVER_DIRECTORY)/dist
	rm -rf $(SERVER_DIRECTORY)/build
	rm -rf $(SERVER_DIRECTORY)/win32/dist
	rm -rf $(SERVER_DIRECTORY)/win32/build
	rm -rf $(SERVER_DIRECTORY)/*.exe
	rm -rf $(SERVER_DIRECTORY)/.cyg*

allinone: server_clean
	cp $(SERVER_DIRECTORY)/requirements.txt $(WINPY32_DIR)/
	-(cd $(WINPY32_DIR) && ./python.exe -m pip install --upgrade pip)
	-(cd $(WINPY32_DIR) && cat requirements.txt | while read PAC ; do Scripts/pip3.exe install "$${PAC}" ; done)
	-(cd $(WINPY32_DIR) && Scripts/pip3.exe freeze)
	rm $(WINPY32_DIR)/requirements.txt
	cp $(SERVER_DIRECTORY)/requirements.txt $(WINPY64_DIR)/
	-(cd $(WINPY64_DIR) && ./python.exe -m pip install --upgrade pip)
	-(cd $(WINPY64_DIR) && cat requirements.txt | while read PAC ; do Scripts/pip3.exe install "$${PAC}" ; done)
	-(cd $(WINPY64_DIR) && Scripts/pip3.exe freeze)
	rm $(WINPY64_DIR)/requirements.txt
	(cd $(SERVER_DIRECTORY)/setup/win32 && $(LAUNCH_MAKENSIS))
	(cd $(SERVER_DIRECTORY)/setup/win32 && mkdir -p $(FILES_DIRECTORY))
	(cd $(SERVER_DIRECTORY)/setup/win32 && cp odoo_setup_*.exe $(FILES_DIRECTORY)/)
	(cd $(SERVER_DIRECTORY)/setup/win32/$(FILES_DIRECTORY) && chmod 0766 odoo_setup_*.exe)
