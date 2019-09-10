ZIP_FILE=../../openerp_report_designer.zip

all: pack uninstall install

create:
	cat script/import \
	    script/lib/actions.py \
	    script/lib/error.py \
	    script/lib/functions.py \
	    script/lib/gui.py \
	    script/lib/tools.py \
	    script/lib/logreport.py\
	    script/lib/rpc.py\
	    script/lib/tiny_socket.py\
	    script/Repeatln.py \
	    script/Fields.py \
	    script/Expression.py \
	    script/modify.py \
	    script/ServerParameter.py \
	    script/Change.py \
	    script/NewReport.py \
	    script/LoginTest.py \
	    script/ModifyExistingReport.py \
	    script/SendToServer.py \
	    script/About.py \
	    script/ConvertBracesToField.py \
	    script/ConvertFieldsToBraces.py \
	    script/ExportToRML.py \
	    script/Translation.py \
	    script/AddAttachment.py > package/OpenERPReport.py

pack: clean create
	zip $(ZIP_FILE) `find package/ | grep -v svn` 
	
install:
	sh /opt/openoffice.org3/program/unopkg add -v $(ZIP_FILE)
	
uninstall:
	sh /opt/openoffice.org3/program/unopkg remove -v  $(ZIP_FILE)

clean:
	rm -f $(ZIP_FILE)
