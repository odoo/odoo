all: compile clean

concat: all.rst
	cat all.rst iPhone.rst evolution.rst > compile.rst
    
compile: concat
	rst2pdf compile.rst -o caldav_doc.pdf 
	
debug: compile

clean:
	rm compile.rst 

del: 
	rm caldav_doc.pdf
