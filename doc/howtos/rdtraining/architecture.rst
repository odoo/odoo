.. _howto/rdtraining/architecture:

=====================
Architecture Overview
=====================

Multitier application
=====================

Odoo follows a `multitier architecture`_ architecture, meaning that the presentation, the business
logic and the data storage are separated. More specifically, it uses a three-tier architecture
(image from Wikipedia):

.. image:: architecture/media/three_tier.svg
    :align: center
    :alt: Three-tier architecture

The presentation tier is a combination of HTML5, JavaScript and CSS. The logic tier is exclusively
written in Python, while the data tier only supports PostgreSQL as an RDBM.

Depending on the scope of your module, the Odoo development can be done in any of these tiers.
Therefore, before going further it may be a good idea to refresh your memory if you don't have
an intermediate level in these topics.

In order to go through this tutorial, you will need very basic HTML knowledge but an intermediate
level of Python. Advanced topics will require more knowledge in the other subjects. There are
plenty of tutorials freely accessible, so we cannot really recommend one more than another;
it all depends on your background.

For reference this is the official `Python tutorial`_.

Odoo modules
============

Both server and client extensions are packaged as *modules* which are
optionally loaded in a *database*. A module is a collection of functions and data that aim a
sole purpose.

Odoo modules can either add brand new business logic to an Odoo system, or
alter and extend existing business logic: a module can be created to add your
country's accounting rules to Odoo's generic accounting support, while the
next module adds support for real-time visualisation of a bus fleet.

Everything in Odoo thus starts and ends with modules.

Composition of a module
-----------------------

An Odoo module **can** contain a number of elements:

Business objects
    A business object (e.g. an invoice) is declared as a Python class. The variables defined in
    these classes are automatically mapped to database fields thanks to the
    :abbr:`ORM (Object-Relational Mapping)` layer.

:ref:`Object views <reference/views>`
    Definition of business objects UI display

:ref:`Data files <reference/data>`
    XML or CSV files declaring the model metadata :

    * :ref:`views <reference/views>` or :ref:`reports <reference/reports>`,
    * configuration data (modules parametrization, :ref:`security rules <reference/security>`),
    * demonstration data
    * and more

:ref:`Web controllers <reference/controllers>`
    Handle requests from web browsers.

Static web data
    Images, CSS or JavaScript files used by the web interface or website

None of these elements is mandatory: some modules may only add data files (e.g. contry-specific
accounting configuration), while others adds business objects. During this training, we will
create business objects, object views and data files. Web controllers and static web data
are the topic of advanced trainings.

Module structure
----------------

Each module is a directory within a *module directory*. Module directories
are specified by using the :option:`--addons-path <odoo-bin --addons-path>`
option.

An Odoo module is declared by its :ref:`manifest <reference/module/manifest>`.

When the Odoo module includes business objects (i.e. Python files), they are organized as a
`Python package <http://docs.python.org/3/tutorial/modules.html#packages>`_
with a ``__init__.py`` file, containing import instructions for various Python
files in the module.

Ready to start? Before writing actual code, let's go to the
:ref:`next chapter <howto/rdtraining/setup>` to review the Odoo installation process. Even if
Odoo is already running on your system, we strongly suggest you go though this chapter
to make sure we are on the same page to start the development of our new application.

.. _multitier architecture:
    https://en.wikipedia.org/wiki/Multitier_architecture

.. _Python tutorial:
    https://docs.python.org/3.6/tutorial/
