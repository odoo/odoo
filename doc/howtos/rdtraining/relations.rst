.. _howto/rdtraining/relations:

========================
Relations Between Models
========================

The :ref:`previous chapter <howto/rdtraining/basicviews>` covered the creation of custom views
for a model containing basic fields. However, in any real business scenario we need more than
one model. Moreover, links between models are necessary. One can easily imagine a model containing
the customers, or another one containing the list of users. You might need to refer to a customer
or a user on any existing business model.

In our real estate module, we want the following information on a property:

- the customer who bought the property
- the real restate agent who sold the property
- the type of the property: house, apartment, penthouse, castle...
- a list of tags characterizing the property: cozy, renovated...
- the list of the offers received

Many2one
========

**Reference**: the documentation related to this topic can be found in
:class:`~odoo.fields.Many2one`.

.. note::

    **Goal**: at the end of this section:
    
    - a new ``estate.property.type`` model is created with the corresponding menu, action and views.

    .. image:: relations/media/property_type.png
        :align: center
        :alt: Property type

    - 3 Many2one fields are added to the ``estate.property`` model: property type, buyer and seller.

    .. image:: relations/media/property_many2one.png
        :align: center
        :alt: Property

In our real estate module, we want to define the concept of property type. A property type
is, for example, a house or an apartment. Indeed, it is a standard business need to categorize
the properties according to their type, in particular to refine the filtering.

A property can have **one** type, but the same type can be assigned on **many** properties:
we will use the **many2one** concept.

A many2one is a simple link to an other object. For example, in order to define a link to the
``res.partner`` on our test model, we could write::

    partner_id = fields.Many2one("res.partner", string="Partner")

By convention, many2one fields have the ``_id`` suffix. Then, accessing the data on the partner is
simply::

    print(my_test_object.partner_id.name)

.. seealso:: `foreign keys <https://www.postgresql.org/docs/current/tutorial-fk.html>`_

 In practice, a many2one can be seen as a dropdown list on a form view.

.. exercise:: Add the Real Estate Property Type table

    - Create the ``estate.property.type`` model and add the following field:

    ========================= ========================= =========================
    Field                     Type                      Attributes
    ========================= ========================= =========================
    name                      Char                      required
    ========================= ========================= =========================

    - Add the menus as displayed in the **Goal**
    - Add the field ``property_type_id`` on your ``estate.property`` model and its form, tree
      and search views

    This excercise is a good recap of the previous chapters: you need to create a
    :ref:`model <howto/rdtraining/basicmodel>`, set the
    :ref:`model <howto/rdtraining/securityintro>`, add an
    :ref:`action and a menu <howto/rdtraining/firstui>`, then
    :ref:`create a view <howto/rdtraining/basicviews>`.

    Tip: do not forget to import any new Python file in ``__init__.py``, add new data files in
    ``__manifest.py__``  and add the access rights ;-)

Once again, restart the server and refresh to see the results!

In the real estate module, there are still two missing information we want on a property: the buyer
and the salesperson. The buyer can be any individual, but on the other end the salesperson must be
an employee of the real estate agency (i.e. an Odoo user).

In Odoo, there are two models to which we commonly refer to:

- ``res.partner``: a partner is a physical or legal entity. It can be a company, an individual, or
  even a contact address.
- ``res.users``: it contains the users of the system. Users can be 'internal': they have
  access to the Odoo backend. Or they can be 'portal': they cannot access the backend, only the
  frontend (e.g. to access their previous orders on the eCommerce).

.. exercise:: Add the buyer and the salesperson

    Add a buyer and a salesperson on the ``estate.property`` model using the two common models
    mentioned. They should be added in a new tab of the form view, as depicted.

    The default value for the salesperson must be the current user. The buyer should not be copied.

    Tip: to get the default value, check the note below or find an example
    `here <https://github.com/odoo/odoo/blob/5bb8b927524d062be32f92eb326ef64091301de1/addons/crm/models/crm_lead.py#L92>`__.

.. note::

    The object ``self.env`` gives access to request parameters and other useful
    things:

    - ``self.env.cr`` or ``self._cr`` is the database *cursor* object; it is
      used for querying the database
    - ``self.env.uid`` or ``self._uid`` is the current user's database id
    - ``self.env.user`` is the current user's record
    - ``self.env.context`` or ``self._context`` is the context dictionary
    - ``self.env.ref(xml_id)`` returns the record corresponding to an XML id
    - ``self.env[model_name]`` returns an instance of the given model
    
Let's now have a look at other types of links.

Many2many
=========

**Reference**: the documentation related to this topic can be found in
:class:`~odoo.fields.Many2many`.

.. note::

    **Goal**: at the end of this section:
    
    - a new ``estate.property.tag`` model is created with the corresponding menu and action.

    .. image:: relations/media/property_tag.png
        :align: center
        :alt: Property tag

    - Tags are added to the ``estate.property`` model:

    .. image:: relations/media/property_many2many.png
        :align: center
        :alt: Property

In our real estate module, we want to define the concept of property tag. A property tag
is, for example, a property which is 'cozy' or 'renovated'.

A property can have **many** tags, and a tag can be assigned to **many** properties:
we will use the **many2many** concept.

A many2many is a bidirectional multiple relationship, any record on one side can be related to any
number of records on the other side.  For example, in order to define a link to the
``account.tax`` model on our test model, we could write::

    tax_ids = fields.Many2many("account.tax", string="Taxes")

By convention, many2many fields have the ``_ids`` suffix. This means that several taxes can be
added to our test model. It behaves as a list of records, meaning that accessing the data must be
done in a loop::

    for tax in my_test_object.tax_ids:
        print(tax.name)

.. exercise:: Add the Real Estate Property Tag table

    - Create the ``estate.property.tag`` model and add the following field:

    ========================= ========================= =========================
    Field                     Type                      Attributes
    ========================= ========================= =========================
    name                      Char                      required
    ========================= ========================= =========================

    - Add the menus as displayed in the **Goal**
    - Add the field ``tag_ids`` on your ``estate.property`` model and it its form and tree views

    Tip: in the view, use the ``widget="many2many_tags"`` attribute as done
    `here <https://github.com/odoo/odoo/blob/5bb8b927524d062be32f92eb326ef64091301de1/addons/crm_iap_lead_website/views/crm_reveal_views.xml#L36>`__.
    We well cover :ref:`later <howto/rdtraining/sprinkles>` the ``widget`` attribute in more
    details. For now, you can try to add or remove it and see the result ;-)

One2many
========

**Reference**: the documentation related to this topic can be found in
:class:`~odoo.fields.One2many`.

.. note::

    **Goal**: at the end of this section:
    
    - A new ``estate.property.offer`` model is created with the corresponding form and tree view.
    - Offers are added to the ``estate.property`` model:

    .. image:: relations/media/property_offer.png
        :align: center
        :alt: Property offers

In our real estate module, we want to define the concept of property offer. A property offer
is an amount a potential buyer offers to the seller. The offer can be lower or higher than the
expected price.

An offer applies to **one** property, but the same property can have **many** offers:
the concept of **many2one** appears once again. However, in this case we want to display the list
of offers for a given property: we will use the **one2many** concept.

A one2many virtual relationship, inverse of a many2one. For example, we defined on our test model
a link to the ``res.partner`` model thanks to the field ``partner_id``. We can defined the inverse
relation, i.e. the list of test models linked to our partner::

    test_ids = fields.One2many("test.model", "partner_id", string="Tests")

The first parameter is called the ``comodel``, while the second parameter is the field we want to
inverse.

By convention, one2many fields have the ``_ids`` suffix. It behaves as a list of records, meaning
that accessing the data must be done in a loop::

    for test in partner.test_ids:
        print(test.name)

.. danger::

    Because a :class:`~odoo.fields.One2many` is a virtual relationship,
    there *must* be a :class:`~odoo.fields.Many2one` field

.. exercise:: Add the Real Estate Property Offer table

    - Create the ``estate.property.offer`` model and add the following fields:

    ========================= ================================ ============= =================
    Field                     Type                             Attributes    Values
    ========================= ================================ ============= =================
    price                     Float
    status                    Selection                        no copy       Accepted, Refused
    partner_id                Many2one (``res.partner``)       required
    property_id               Many2one (``estate.property``)   required
    ========================= ================================ ============= =================

    - Create a tree and form view with the ``price``, ``partner_id`` and ``status`` fields. No
      need for an action nor a menu.
    - Add the field ``offer_ids`` on your ``estate.property`` model and in its form view as
      depicted.

There are several important things to notice here. First, we don't need an action or a menu for all
models. Some models are intended to be accessed only through another one. This is the case in our
exercise: an offer is always accessed through a property.

Second, despite the fact that the ``property_id`` field is required, we did not include it in the
views. How comes the Odoo knows to which property our offer is linked to? Well that's part of the
magic of using the Odoo framework: sometimes, things are defined implicitly.

Still alive? This chapter is surely not the easiest one. It introduced a couple of new concepts
while relying on everything that was introduced before. The
:ref:`next chapter <howto/rdtraining/compute_onchange>` will be lighter, don't worry ;-)
