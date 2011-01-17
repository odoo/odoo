==========================
CalDAV with iPhone How-To
==========================

For SSL specific configuration see the documentation below

Now, to setup the calendars, you need to:

1. Click on the "Settings" and go to the "Mail, Contacts, Calendars" page.
2. Go to "Add account..."
3. Click on "Other"
4. From the "Calendars" group, select "Add CalDAV Account"

5. Enter the host's name 
   (ie : if the url is http://openerp.com:8069/webdav/db_1/calendars/ , openerp.com is the host)

6. Fill Username and password with your openerp login and password

7. As a description, you can either leave the server's name or
   something like "OpenERP calendars".

9. If you are not using a SSL server, you'll get an error, do not worry and push "Continue"

10. Then click to "Advanced Settings" to specify the right
    ports and paths. 
    
11. Specify the port for the OpenERP server: 8071 for SSL, 8069 without.

12. Set the "Account URL" to the right path of the OpenERP webdav:
    the url given by the wizard (ie : http://my.server.ip:8069/webdav/dbname/calendars/ )

11. Click on Done. The phone will hopefully connect to the OpenERP server
    and verify it can use the account.

12. Go to the main menu of the iPhone and enter the Calendar application.
    Your OpenERP calendars will be visible inside the selection of the
    "Calendars" button.
    Note that when creating a new calendar entry, you will have to specify
    which calendar it should be saved at.



IF you need SSL (and your certificate is not a verified one, as usual),
then you first will need to let the iPhone trust that. Follow these
steps:

    s1. Open Safari and enter the https location of the OpenERP server:
      https://my.server.ip:8071/
      (assuming you have the server at "my.server.ip" and the HTTPS port
      is the default 8071)
    s2. Safari will try to connect and issue a warning about the certificate
      used. Inspect the certificate and click "Accept" so that iPhone
      now trusts it.



