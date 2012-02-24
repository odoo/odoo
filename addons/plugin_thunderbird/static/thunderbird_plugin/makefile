all: xpi

jar:
	jar cvf chrome/openerp_plugin.jar -C chrome/openerp_plugin/ .

xpi: jar
	zip -r ../openerp_plugin.xpi *

clean:
	rm ../openerp_plugin.xpi
	rm chrome/openerp_plugin.jar
