.. _howto/rdtraining/newapp:

=================
A New Application
=================

The purpose of this chapter is to lay the basis for the creation of a completely new Odoo module.
We will start from scratch with the minimum necessary to have our module recognized by Odoo.
During the next chapters, we will progressively add features to build a realistic business case.

The Real Estate Advertisement module
====================================

Our new module will cover a business area which is very specific, and therefore not included in the
standard set of modules: the real estate properties. It is worth noting that before
developing a new module, it always makes sense to verify if Odoo doesn't already provide a way
to answer the specific business needs.

Here is an overview of the main list view containing some advertisements:

.. image:: newapp/media/overview_list_view_01.png
   :align: center
   :alt: List view 01

The top area of the form view summarizes important information for the property, such as the name,
the property type, the postcode and so on. The first tab contains information describing the 
property: bedrooms, living area, garage, garden...

.. image:: newapp/media/overview_form_view_01.png
   :align: center
   :alt: Form view 01

The second tab lists off the offers for the property. Indeed, potential buyers may offer more or
less than the expected selling price. It is up to the seller to accept an offer.

.. image:: newapp/media/overview_form_view_02.png
   :align: center
   :alt: Form view 02

Here is a quick video showing the workflow of the module.

TODO: video showing features

Prepare the addon directory
===========================

**Reference**: the documentation related to this topic can be found in
:ref:`manifest <reference/module/manifest>`.

.. note::

   **Goal**: the goal of this section is to have Odoo recognize our new module, which will still
   be an empty shell. It will be listed in the Apps:

   .. image:: newapp/media/app_in_list.png
      :align: center
      :alt: The new module appears in the list

The very first step of a module creation is to create a new folder. To ease the development, we
suggest you first create the folder ``/home/$USER/src/custom``. In this folder we add the folder
``estate``, which is our module.

A module must contain at least 2 files: the ``__manifest__.py`` file and a ``__init__.py`` file.
The ``__init__.py`` file can remain empty for now, so we'll come back to it in the next chapter.
The ``__manifest__.py`` file, on the other hand, must describe our module and cannot remain empty.
Its only required field is the ``name``, but it usually contains much more information.

Take a look at the
`CRM file <https://github.com/odoo/odoo/blob/fc92728fb2aa306bf0e01a7f9ae1cfa3c1df0e10/addons/crm/__manifest__.py#L1-L67>`__
as an example. On top of providing the description of the module (``name``, ``category``,
``summary``, ``website``...), it lists its dependencies (``depends``). A dependency means that the
Odoo framework will ensure that these are installed before our module is installed. Moreover, if
one of the dependency is uninstalled our module will also be uninstalled. Think about your favorite
Linux distribution packaging tool (``apt``, ``dnf``, ``pacman``...): Odoo works in the same fashion.

.. exercise:: Creation the required addon files

    Create the following folders and files:

    - ``/home/$USER/src/custom/estate/__init__.py``
    - ``/home/$USER/src/custom/estate/__manifest__.py``

    The ``__manifest__.py`` file should only define the name and the dependencies of our modules.
    Two framework modules are necessary: ``base`` and ``web``.


Restart the Odoo server and add the ``custom`` folder to the ``addons-path``:

.. code-block:: console

    $ ./odoo-bin --addons-path=../custom,../enterprise/,addons

Go to Apps, click on Update Apps List, search for ``estate`` and... tadaaa, you module appears!
No, it doesn't appear? Maybe try to remove the default 'Apps' filter ;-)

.. exercise:: Make your module an 'App'

    Add the appropriate key to your ``__manifest__.py`` so that the module appears when the 'Apps'
    filter is on.

You can even install the module! But obviously it's an empty shell, so no menu will appear.

It's all good? If so, let's :ref:`create our first table <howto/rdtraining/basicmodel>`!
