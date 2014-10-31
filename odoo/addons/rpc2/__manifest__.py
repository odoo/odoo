# -*- coding: utf-8 -*-
{
    'name': "RPC2",
    'description': """
Replacement XML-RPC layer
=========================

* Aims to call into the new API instead of the old one, preparing the ultimate
  deprecation and removal of old-style calls
  - pass ids and context as explicit parameters so a correct `Environment` and
    "record" can be created before calling the requested method
  - serialize recordset at the XML-RPC boundary instead of... elsewhere?
* Aims to better use XML-RPC and better integrate with what XML-RPC libraries
  support
  - /RPC2/ path (used in examples, default path in Ruby stdlib)
  - HTTP Basic Auth instead of own scheme, directly integrated in most
    libraries
  - fully dotted path instead of multiple endpoints, some libraries (e.g.
    Python stdlib) can use proxy chains transparently
""",

    'category': 'Uncategorized',
    'version': '0.1',
    'depends': ['base'],
    'auto_install': True,
}
