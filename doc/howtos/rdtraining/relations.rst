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

    **Goal**: at the end of this section
    
    - a new ``estate.property.type`` model is created with the corresponding menu, action and views.
    - 3 Many2one fields are added to the ``estate.property`` model: property type, buyer and seller.

    .. image:: relations/media/property_type.png
      :align: center
      :alt: Property type

    .. image:: relations/media/property.png
      :align: center
      :alt: Property

Many2many
=========
(property tag)

One2many
========
(property offer)
