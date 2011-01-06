==========================
CalDAV with iPhone How-To
==========================

As from OpenERP v6.0, document_webdav v2.2, the iPhone has been thoroughly
tested and supported as a Calendaring client for the OpenERP CalDAV module.

However, keep in mind that OpenERP is not a straightforward calendaring
server, but an ERP application (with more data + structure) which exposes
that data to calendar clients. That said, the full features that would be
accessible through the Gtk or Web OpenERP clients cannot be crammed into
the Calendar clients (such as the iPhone).


Phone setup
-------------
The iPhone is fairly easy to setup.
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

Now, to setup the calendars, you need to:
1. Click on the "Settings" and go to the "Mail, Contacts, Calendars" page.
2. Go to "Add account..."
3. Click on "Other"
4. From the "Calendars" group, select "Add CalDAV Account"
5. Enter the server's name or IP address at the "Server" entry, the
      OpenERP username and password at the next ones.
      As a description, you can either leave the server's name or
      something like "OpenERP calendars".
6. You _will_ get the "Unable to verify account" error message. That is
      because our server is not at the port iPhone expects[2]. But no
      need to worry, click OK.
7. At the next page, enter the "Advanced Settings" to specify the right
      ports and paths 
8. If you have SSL, turn the switch on. Note that port will be changed
      to 8443.
9. Specify the port for the OpenERP server: 8071 for SSL, 8069 without.
10. Set the "Account URL" to the right path of the OpenERP webdav:
      https://my.server.ip:8071/webdav/dbname/calendars
      Where "https://my.server.ip:8071" is the protocol, server name 
      and port as discussed above, "dbname" is the name of the database.
      [Note that the default 
      "https://my.server.ip:8071/principals/users/username" might also
      be edited to 
      "https://my.server.ip:8071/webdav/dbname/principals/users/username" ]
11. Click on Done. The phone will hopefully connect to the OpenERP server
      and verify it can use the account.
12. Go to the main menu of the iPhone and enter the Calendar application.
      Your OpenERP calendars will be visible inside the selection of the
      "Calendars" button.
    Note that when creating a new calendar entry, you will have to specify
    which calendar it should be saved at.





[2] This may not happen if the SRV records at DNS and the well-known URIs
are setup right. But we appreciate that a default OpenERP installation will
not have the DNS server of the company's domain configured.
