all:
	(cd openoffice_report && make pack)
	cp openoffice_report/*.zip .
	(cd openoffice_report_designer/bin && make pack)
	cp openoffice_report_designer/bin/*.zip .


clean:
	rm -f *.zip
	(cd openoffice_report && make clean)
	(cd openoffice_report_designer/bin && make clean)

