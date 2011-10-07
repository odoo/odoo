===============================
Discovery of calendar resources
===============================

1. Srv record
--------------
Calendar server and port should be advertised by a DNS _srv record. 
Although this is beyond the capabilities of the OpenERP server, an
example setup is listed below:
    -- TODO --
    
DNS -> http://our-host-ip:port/

2. Well-known uris
-------------------
The OpenERP server may have the 'well-known URIs' servlet activated,
which means that it will advertise its main database and the correct
location of the main CalDAV resource.
http://our-host-ip:port/.well-known/caldav -> http://our-host-ip:port/webdav/dbname/calendars/


3. Caldav collection
---------------------
The CalDAV "collection" is not necessarily a calendar or a folder just
containing calendars under it. It is a DAV resource (aka folder) which
has special DAV properties, so that clients are redirected to the right
urls (like per-user calendars etc.).

http://our-host-ip:port/webdav/dbname/calendars/ -> http://our-host-ip:port/webdav/dbname/calendars/users/user-login/c/

4. Calendar home for user
--------------------------
There can be one dynamic folder per user, which will in turn contain the calendars

http://our-host-ip:port/webdav/dbname/calendars/users/user-login/c/ ->
http://our-host-ip:port/webdav/dbname/calendars/users/user-login/c/[Meetings, Tasks]

5. Calendars 
--------------
Each calendar will contain the resource nodes:
  .../c/Meetings/ -> .../c/Meetings/123.ics

Principal url
