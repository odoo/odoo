==========================
CalDAV How-To
==========================


As from OpenERP v6.0, document_webdav v2.2, the iPhone has been thoroughly
tested and supported as a Calendaring client for the OpenERP CalDAV module.

However, keep in mind that OpenERP is not a straightforward calendaring
server, but an ERP application (with more data + structure) which exposes
that data to calendar clients. That said, the full features that would be
accessible through the Gtk or Web OpenERP clients cannot be crammed into
the Calendar clients (such as the iPhone). 

OpenERP server Setup
--------------------
Some modules need to be installed at the OpenERP server. These are:
    - caldav: Required, has the reference setup and the necessary
            underlying code. Will also cause document, document_webdav
            to be installed.
    - crm_caldav: Optional, will export the CRM Meetings as a calendar.
    - project_caldav: Optional, will export project tasks as calendar.
    - http_well_known: Optional, experimental. Will ease bootstrapping,
            but only when a DNS srv record is also used.

These will also install a reference setup of the folders, ready to go.
The administrator of OpenERP can add more calendars and structure, if
needed.

DNS server setup
------------------
To be documented.

SSL setup
----------
It is highly advisable that you also setup SSL to work for the OpenERP
server. HTTPS is a server-wide feature in OpenERP, which means a 
certificate will be set at the openerp-server.conf and will be the same
for XML-RPC, HTTP, WebDAV and CalDAV.
The iPhone also supports secure connections with SSL, although it does
not expect a self-signed certificate (or one that is not verified by
one of the "big" certificate authorities [1] ).


[1] I remember one guy that made *lots* of money selling his CA business
off, and since then uses this money to create a software monopoly.




