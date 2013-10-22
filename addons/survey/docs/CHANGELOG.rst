OpenERP Survey Module Changelog
===============================


:Author:    Richard Mathot (OpenERP) <rim@openerp.com>
:Date:      October 2013


Preamble
--------

As large parts of this module (have been||will be) rewritten, this document attemps to list all the changes that have been made to models.

Model changes
-------------

* ``survey_type`` is removed. The field ``survey_type.name`` is replaced by 
  ``srvey.category`` and is not mandatory anymore.
* 

.. note::
    Some fields have been renamed inside models; in this case attribute ``oldname`` has always been used to ensure smooth database migration.


Something not listed here?
--------------------------

**Please submit a patch with missing stuff!**

.. warning::
    If you don't submit corrections to documentation, a giant worm could eat your house... ;-)
