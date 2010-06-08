Steps to Install package in Openoffice

	- In Openoffice writer select Tools Menu

	- Inside of Tools menu you will get option like "Package Manager"

	- Select Package Manager you will get one dialog box

	- In Dialog box you will get one listbox below "Browse Packages". 
	  You will find different options like 'My Packages,
	  Openoffice Packages'.

	- You have select 'My Packages' and then click on button named 'Add...' 
	  then select your path where the package is located that is 
	  ZIP archive file.

	- On the completion of adding package you will get your package
	  under 'My Packages' and the status of your package become 'Enabled'
	  then close openoffice writer

	- Now you have start tiny server

	- then in unother terminal u have to write command 

		ooffice "-accept=socket,host=localhost,port=2002;urp;"

	- Above command will open openoffice writer with socket connection
	  if you use different host then localhost then chang it accordingly

	- Now in openoffice writer u will find one new menu named "Tiny Report"

Steps to execute scripts 

	- You can directly us scripts for perticular operation.

	- If you want to execute script then u have to use terminal.

	- Now you have start tiny server

	- then in unother terminal u have to write command 

		ooffice "-accept=socket,host=localhost,port=2002;urp;"

	- Go to the perticular directory of scripts and then use below command
		
		python scriptname.py

	- you will get execute yor script
