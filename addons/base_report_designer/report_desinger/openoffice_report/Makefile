ZIP_FILE=openerp_report_add_attachment.zip

all: create pack uninstall install

create:
	cat script/import \
	    script/lib/actions.py \
	    script/lib/error.py \
	    script/lib/functions.py \
	    script/lib/gui.py \
	    script/lib/tools.py \
	    script/Change.py \
	    script/LoginTest.py \
	    script/AddAttachment.py \
	    script/ServerParameter.py \
	    script/About.py > package/OpenERPReport.py

pack: clean
	zip $(ZIP_FILE) `find package/ | grep -v svn` 
	
install:
	sh /usr/lib/openoffice/program/unopkg add -v $(ZIP_FILE)
	
uninstall:
	sh /usr/lib/openoffice/program/unopkg remove -v  $(ZIP_FILE)

clean:
	rm -f $(ZIP_FILE)
