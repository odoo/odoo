include Makefile.version

SERVER_DIRECTORY=../server
FILES_DIRECTORY=files

LAUNCH_PY2EXE=/cygdrive/c/python26/python.exe setup.py py2exe

MAKENSIS_ARGUMENTS=/DVERSION=$(VERSION)

LAUNCH_MAKENSIS=/cygdrive/c/cygwin/makensis $(MAKENSIS_ARGUMENTS) setup.nsi

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

server: server_clean
	(cd $(SERVER_DIRECTORY)/win32 && $(LAUNCH_PY2EXE))
	(cd $(SERVER_DIRECTORY) && $(LAUNCH_PY2EXE))
#	rm -rf `/usr/bin/find ${SERVER_DIRECTORY}/dist/openerp/addons -maxdepth 1 -mindepth 1 -not -name "web*" -and -not -name "base" -type d | xargs rm -rf`
	(cd $(SERVER_DIRECTORY) && $(LAUNCH_MAKENSIS))
	cp $(SERVER_DIRECTORY)/openerp-*.exe $(FILES_DIRECTORY)/openerp-server-setup-$(VERSION).exe

allinone: server
	$(LAUNCH_MAKENSIS)
	cp ./openerp-*.exe $(FILES_DIRECTORY)/openerp-allinone-setup-$(VERSION).exe

