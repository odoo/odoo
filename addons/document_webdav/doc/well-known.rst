=================
Well-known URIs
=================

In accordance to IETF RFC 5785 [1], we shall publish a few locations
on the root of our http server, so that clients can discover our 
services (CalDAV, eg.).

This module merely installs a special http request handler, that will
redirect the URIs from "http://our-server:port/.well-known/xxx' to 
the correct path for each xxx service.

Note that well-known URIs cannot have a database-specific behaviour, 
they are server-wide. So, we have to explicitly chose one of our databases
to serve at them. By default, the database of the configuration file
is chosen

Example config:

[http-well-known]
num_services = 2
db_name = openerp-main ; must define that for path_1 below
service_1 = caldav
path_1 = /webdav/%(db_name)s/Calendars/
service_2 = foo
path_2 = /other_db/static/Foo.html


[1] http://www.rfc-editor.org/rfc/rfc5785.txt