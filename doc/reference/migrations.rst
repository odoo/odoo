:banner: banners/migration.jpg

.. _reference/migrations:

=================
Migrating Modules
=================

Odoo comes bundled with powerful migration tools and behaviours. While the Odoo
Framework does much of the work for you when you increment your module version
and modify your code, you might need to write *migration scripts* to ensure a
smooth upgrade of your module.

.. _reference/migrations/automatic:

Automatic migration framework
=============================

explain how the orm does a lot for you:
    - new tables and columns created automatically
    - computed fields computed automatically
    - xml files reloaded automatically

.. _reference/migrations/custom:

Custom migration scripts
========================

explain when it can be useful:
    - module changes (deps, renaming, dropping, merging, etc.)
    - model/fields changes (renaming, deletion, recompute, etc.)

explain how to use:
    - `migrations` folder
    - need a `migrate` function in python scripts
    - `from odoo import migration`

Loading order
-------------

explain the `pre`-`post`-`end` + sequence syntax

Content
-------

show example using the cursor, utilities and/or sql code directly

.. _reference/migrations/utils:

Migration utilities
===================

detail the most useful functions of the migration utilities
