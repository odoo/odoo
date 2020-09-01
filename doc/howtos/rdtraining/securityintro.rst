.. _howto/rdtraining/securityintro:

===============================
Security - A Brief Introduction
===============================

In the :ref:`previous chapter <howto/rdtraining/basicmodel>`, we created our first table intended
to store business data. In a business application such as Odoo, one of the first question to raise
is to know who\ [#who]_ can access the data. Odoo provides a security mechanism to allow access
to the data to some groups of users.

The security topic is covered in more details in an appendix. This chapter aims to cover the
minimum required to use our new module.

Data Files (CSV)
================

Odoo is a highly data driven system. Although behavior is customized using Python code part of a
module's value is in the data it sets up when loaded. One way to load the data is through a CSV
file. For example, the
`list of country states <https://github.com/odoo/odoo/blob/master/odoo/addons/base/data/res.country.state.csv>`__
is loaded at installation of the ``base`` module.

.. code-block:: text

    "id","country_id:id","name","code"
    state_us_1,us,"Alabama","AL"
    state_us_2,us,"Alaska","AK"
    state_us_3,us,"Arizona","AZ"
    state_us_4,us,"Arkansas","AR"
    ...

- ``id`` is an :term:`external identifier`, it allows referring to the record
  (without having to know its in-database identifier).
- ``country_id:id`` refers to the country by using its :term:`external identifier`.
- ``name`` is the name of the state.
- ``code`` is the code of the state.

These three fields are
`defined <https://github.com/odoo/odoo/blob/2ad2f3d6567b6266fc42c6d2999d11f3066b282c/odoo/addons/base/models/res_country.py#L108-L111>`__
in the ``res.country.state`` model.

By convention, a file importing data is located in the ``data`` folder of a module. When the data
is related to security, it is located in the ``security`` folder. Moreover, such
file must be declared in the ``__manifest__.py`` file, in the ``data`` list. In our example, the
file is defined
`in the manifest of the base module <https://github.com/odoo/odoo/blob/e8697f609372cd61b045c4ee2c7f0fcfb496f58a/odoo/addons/base/__manifest__.py#L29>`__.

Finally, note that the content of the data files is only loaded when a module is installed or
updated.

.. warning::

    The data files are loaded sequencially following their order in the ``__manifest__.py`` file.
    This means that if a data ``A`` refers to another data ``B``, you must make sure that ``B``
    is loaded before ``A``.

    In the case our the country states, you will note that the
    `list of countries <https://github.com/odoo/odoo/blob/e8697f609372cd61b045c4ee2c7f0fcfb496f58a/odoo/addons/base/__manifest__.py#L22>`__
    is loaded **before** the
    `list of country states <https://github.com/odoo/odoo/blob/e8697f609372cd61b045c4ee2c7f0fcfb496f58a/odoo/addons/base/__manifest__.py#L29>`__.
    This is logical since the states refer to the countries.

Why is all this important for the security? Because all the security of a model is loaded through
data files, as we'll see in the next section.

Access Rights
=============

**Reference**: the documentation related to this topic can be found in
:ref:`reference/security/acl`.

.. note::

    **Goal**: at the end of this section, the following warning should not appear anymore:

    .. code-block:: text

        WARNING rd-demo odoo.modules.loading: The model estate.property has no access rules...

When no access rights is defined on a model, Odoo considers that no user can access the data.
It is actually notified in the log:

.. code-block:: text

    WARNING rd-demo odoo.modules.loading: The model estate.property has no access rules, consider adding one. E.g. access_estate_property,access_estate_property,model_estate_property,base.group_user,1,0,0,0

Access rights are defined as records of the model ``ir.model.access``. Each
access right is associated to a model, a group (or no group for global
access), and a set of permissions: read, write, create, unlink. Such access
rights are usually created by a CSV file named after its model:
``ir.model.access.csv``.

Here is an example for our former ``test.model``:

.. code-block:: text

    id,name,model_id/id,group_id/id,perm_read,perm_write,perm_create,perm_unlink
    access_test_model,access_test_model,model_test_model,base.group_user,1,0,0,0

- ``id`` is an :term:`external identifier`.
- ``name`` is the name of the ``ir.model.access``.
- ``model_id/id`` refers to the model to which the access right applies. The standard way to refer
  to the model is ``model_<model_name>``, where ``<model_name>`` is the ``_name`` of the model,
  with the ``.`` replaced by ``_``. Seems cumbersome? Indeed...
- ``group_id/id`` refers to the group to which the access right applies. We will cover the concept
  of group in the appendix dedicated to the security.
- ``perm_read,perm_write,perm_create,perm_unlink``: read, write, create and unlink permissions

.. exercise:: Add access rights.

    Create the ``ir.model.access.csv`` file in the appropriate folder and define it in the
    ``__manifest__.py`` file.

    Give the read, write, create and unlink permissions to the group ``base.group_user``.

    Tip: the warning message in the log gives you most of the solution ;-)

Restart the server, and the warning message should have disappeared!

.. [#who] 'who' means which Odoo user
