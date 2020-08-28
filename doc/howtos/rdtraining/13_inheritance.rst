.. _howto/rdtraining/13_inheritance:

=======================
Chapter 13: Inheritance
=======================

A powerful aspect of Odoo is its modularity. A module is dedicated to a business need, but
modules can also interact with one another. This is useful for extending the functionality of an existing
module. For example, in our real estate scenario we want to display the list of a salesperson's properties
directly in the regular user view.

But before going through the specific Odoo module inheritance, let's see how we can alter the
behavior of the standard CRUD (Create, Retrieve, Update or Delete) methods.

Python Inheritance
==================

.. note::

    **Goal**: at the end of this section:

    - It should not be possible to delete a property which is not new or canceled.

    .. image:: 13_inheritance/media/unlink.gif
        :align: center
        :alt: Unlink

    - When an offer is created, the property state should change to 'Offer Received'
    - It should not be possible to create an offer with a lower price than an existing offer

    .. image:: 13_inheritance/media/create.gif
        :align: center
        :alt: Create

In our real estate module, we never had to develop anything specific to be able to do the
standard CRUD actions. The Odoo framework provides the necessary
tools to do them. In fact, such actions are already included in our model thanks to classical
Python inheritance::

    from odoo import fields, models

    class TestModel(models.Model):
        _name = "test.model"
        _description = "Test Model"

        ...

Our ``class TestModel`` inherits from :class:`~odoo.models.Model` which provides
:meth:`~odoo.models.Model.create`, :meth:`~odoo.models.Model.read`, :meth:`~odoo.models.Model.write`
and :meth:`~odoo.models.Model.unlink`.

These methods (and any other method defined on :class:`~odoo.models.Model`) can be extended to add
specific business logic::

    from odoo import fields, models

    class TestModel(models.Model):
        _name = "test.model"
        _description = "Test Model"

        ...

        @api.model
        def create(self, vals):
            # Do some business logic, modify vals...
            ...
            # Then call super to execute the parent method
            return super().create(vals)

The decorator :func:`~odoo.api.model` is necessary for the :meth:`~odoo.models.Model.create`
method because the content of the recordset ``self`` is not relevant in the context of creation,
but it is not necessary for the other CRUD methods.

In Python 3, ``super()`` is equivalent to ``super(TestModel, self)``. The latter may be necessary
when you need to call the parent method with a modified recordset.

.. danger::

    - It is very important to **always** call ``super()`` to avoid breaking the flow. There are
      only a few very specific cases where you don't want to call it.
    - Make sure to **always** return data consistent with the parent method. For example, if
      the parent method returns a ``dict()``, your override must also return a ``dict()``.

.. exercise:: Add business logic to the CRUD methods.

    - Prevent deletion of a property if its state is not 'New' or 'Canceled'

    Tip: override :meth:`~odoo.models.Model.unlink` and remember that ``self`` can be a recordset
    with more than one record.

    - At offer creation, set the property state to 'Offer Received'. Also raise an error if the user
      tries to create an offer with a lower amount than an existing offer.

    Tip: the ``property_id`` field is available in the ``vals``, but it is an ``int``. To
    instantiate an ``estate.property`` object, use ``self.env[model_name].browse(value)``
    (`example <https://github.com/odoo/odoo/blob/136e4f66cd5cafe7df450514937c7218c7216c93/addons/gamification/models/badge.py#L57>`__)

Model Inheritance
=================

**Reference**: the documentation related to this topic can be found in
:ref:`reference/orm/inheritance`.

In our real estate module, we would like to display the list of properties linked to a salesperson
directly in the Settings / Users & Companies / Users form view. To do this, we need to add a field to
the ``res.users`` model and adapt its view to show it.

Odoo provides two *inheritance* mechanisms to extend an existing model in a modular way.

The first inheritance mechanism allows modules to modify the behavior of a model defined in an
another module by:

- adding fields to the model,
- overriding the definition of fields in the model,
- adding constraints to the model,
- adding methods to the model,
- overriding existing methods in the model.

The second inheritance mechanism (delegation) allows every record of a model to be linked
to a parent model's record and provides transparent access to the
fields of this parent record.

.. image:: 13_inheritance/media/inheritance_methods.png
    :align: center
    :alt: Inheritance Methods

In Odoo, the first mechanism is by far the most used. In our case, we want to add a field to an
existing model, which means we will use the first mechanism. For example::

    from odoo import fields, models

    class InheritedModel(models.Model):
        _inherit = "inherited.model"

        new_field = fields.Char(string="New Field")

A practical example where two fields are added to
a model can be found
`here <https://github.com/odoo/odoo/blob/60e9410e9aa3be4a9db50f6f7534ba31fea3bc29/addons/account_fleet/models/account_move.py#L39-L47>`__.

By convention, each inherited model is defined in its own Python file. In our example, it would be
``models/inherited_model.py``.

.. exercise:: Add a field to Users.

    - Add the following field to ``res.users``:

    ===================== ======================================================
    Field                 Type
    ===================== ======================================================
    property_ids          One2many inverse of ``user_id`` to ``estate.property``
    ===================== ======================================================

    - Add a domain to the field so it only lists the available properties.

Now let's add the field to the view and check that everything is working well!

View Inheritance
================

**Reference**: the documentation related to this topic can be found in
:ref:`reference/views/inheritance`.

.. note::

    **Goal**: at the end of this section, the list of available properties linked
    to a salesperson should be displayed in their user form view

    .. image:: 13_inheritance/media/users.png
        :align: center
        :alt: Users

Instead of modifying existing views in place (by overwriting them), Odoo
provides view inheritance where children 'extension' views are applied on top of
root views. These extension can both add and remove content from their parent view.

An extension view references its parent using the ``inherit_id`` field.
Instead of a single view, its ``arch`` field contains a number of
``xpath`` elements that select and alter the content of their parent view:

.. code-block:: xml

    <record id="inherited_model_view_form" model="ir.ui.view">
        <field name="name">inherited.model.form.inherit.test</field>
        <field name="model">inherited.model</field>
        <field name="inherit_id" ref="inherited.inherited_model_view_form"/>
        <field name="arch" type="xml">
            <!-- find field description and add the field
                 new_field after it -->
            <xpath expr="//field[@name='description']" position="after">
              <field name="new_field"/>
            </xpath>
        </field>
    </record>

``expr``
    An XPath_ expression selecting a single element in the parent view.
    Raises an error if it matches no element or more than one
``position``
    Operation to apply to the matched element:

    ``inside``
        appends ``xpath``'s body to the end of the matched element
    ``replace``
        replaces the matched element with the ``xpath``'s body, replacing any ``$0`` node occurrence
        in the new body with the original element
    ``before``
        inserts the ``xpath``'s body as a sibling before the matched element
    ``after``
        inserts the ``xpaths``'s body as a sibling after the matched element
    ``attributes``
        alters the attributes of the matched element using the special
        ``attribute`` elements in the ``xpath``'s body

When matching a single element, the ``position`` attribute can be set directly
on the element to be found. Both inheritances below have the same result.

.. code-block:: xml

    <xpath expr="//field[@name='description']" position="after">
        <field name="idea_ids" />
    </xpath>

    <field name="description" position="after">
        <field name="idea_ids" />
    </field>

An example of a view inheritance extension can be found
`here <https://github.com/odoo/odoo/blob/691d1f087040f1ec7066e485d19ce3662dfc6501/addons/account_fleet/views/account_move_views.xml#L3-L17>`__.

.. exercise:: Add fields to the Users view.

    Add the ``property_ids`` field to the ``base.view_users_form`` in a new notebook page.

    Tip: an example an inheritance of the users' view can be found
    `here <https://github.com/odoo/odoo/blob/691d1f087040f1ec7066e485d19ce3662dfc6501/addons/gamification/views/res_users_views.xml#L5-L14>`__. 

Inheritance is extensively used in Odoo due to its modular concept. Do not hesitate to read
the corresponding documentation for more info!

In the :ref:`next chapter <howto/rdtraining/14_other_module>`, we will learn how to interact with
other modules.

.. _XPath: http://w3.org/TR/xpath
