.. _howto/rdtraining/compute_onchange:

=============================
Computed Fields And Onchanges
=============================

The :ref:`relations between models <howto/rdtraining/relations>` is a key component of any Odoo
module. It is necessary to the modelization of any business case: models are linked one to another.
However, we might want links between the fields inside of a given model. Sometimes because the
value of a field is determined from the value of other fields, sometimes to help the user encoding.

Although this chapter is not technically complex, the semantic of both concepts is very important.
This is also the first time we will write Python logic. Up to now, we never wrote anything else
that class definiton or field declaration.

Computed Fields
===============

**Reference**: the documentation related to this topic can be found in
:ref:`reference/fields/compute`.

.. note::

    **Goal**: at the end of this section:

    - On the property model, the total area and the best offer are computed:

    .. image:: compute_onchange/media/compute.gif
        :align: center
        :alt: Compute fields

    - On the property offer model, the validity date is computed and has an inverse:

    .. image:: compute_onchange/media/compute_inverse.gif
        :align: center
        :alt: Compute field with inverse

In our real estate module, we have defined the living area as well as the garden area. It is then
natural to define the total area as the sum of both fields. We will use the concept of computed
field for this: the value of a given field is computed from the value of other fields.

So far fields have been stored directly in and retrieved directly from the
database. Fields can also be *computed*. In that case, the field's value is not
retrieved from the database but computed on-the-fly by calling a method of the
model.

To create a computed field, create a field and set its attribute
:attr:`~odoo.fields.Field.compute` to the name of a method. The computation
method should simply set the value of the field to compute on every record in
``self``.

By convention, :attr:`~odoo.fields.Field.compute` are private methods, meaning that they cannot
be called from the presentation tier, only from the business tier (see
:ref:`howto/rdtraining/architecture`). Such methods have a name starting with an underscore ``_``.

Dependencies
------------

The value of a computed field usually depends on the values of other fields on
the computed record. The ORM expects the developer to specify those dependencies
on the compute method with the decorator :func:`~odoo.api.depends`.
The given dependencies are used by the ORM to trigger the recomputation of the
field whenever some of its dependencies have been modified::

    from odoo import api, fields, models

    class TestComputed(models.Model):
        _name = "test.computed"

        total = fields.Float(compute="_compute_total")
        amount = fields.Float()

        @api.depends("amount")
        def _compute_total(self):
            for record in self:
                record.total = 2.0 * record.amount

.. note:: ``self`` is a collection
    :class: aphorism

    The object ``self`` is a *recordset*, i.e. an ordered collection of
    records. It supports the standard Python operations on collections, like
    ``len(self)`` and ``iter(self)``, plus extra set operations like ``recs1 +
    recs2``.

    Iterating over ``self`` gives the records one by one, where each record is
    itself a collection of size 1. You can access/assign fields on single
    records by using the dot notation, like ``record.name``.

Many examples of computed fields can be found in Odoo.
`Here <https://github.com/odoo/odoo/blob/713dd3777ca0ce9d121d5162a3d63de3237509f4/addons/account/models/account_move.py#L3420-L3423>`__
is a simple one. 

.. exercise:: Compute the total area

    - Add the ``total_area`` field to ``estate.property``. It is defined as the sum of the
      ``living_area`` and the ``garden_area``.

    - Add the field in the form view as depicted on the first image of the **Goal**.

Relational fields can also be used as dependencies::

    description = fields.Char(compute="_compute_description")
    partner_id = fields.Many2one("res.partner")

    @api.depends("partner_id.name")
    def _compute_description(self):
        for record in self:
            record.description = "Test for partner %s" % record.partner_id.name

The example is given with a :class:`~odoo.fields.Many2one`, but it is valid for
:class:`~odoo.fields.Many2many` or a :class:`~odoo.fields.One2many`. An example can be found
`here <https://github.com/odoo/odoo/blob/713dd3777ca0ce9d121d5162a3d63de3237509f4/addons/account/models/account_reconcile_model.py#L248-L251>`__.

Let's try it on our module with the following exercise!

.. exercise:: Compute the best offer

    - Add the ``best_price`` field to ``estate.property``. It is defined as the maximum of the
      offers' ``price``.

    - Add the field in the form view as depicted on the first image of the **Goal**.

    Tip: you might want to give a try to the :meth:`~odoo.models.BaseModel.mapped` method. See
    `here <https://github.com/odoo/odoo/blob/f011c9aacf3a3010c436d4e4f408cd9ae265de1b/addons/account/models/account_payment.py#L686>`__
    for a simple example.

Inverse Function
----------------

You might have noticed that computed fields are read-only by default. This is expected since the
user is not supposed to set any value.

In some cases, it might be useful to be able to set a value directly. In our real estate example,
we can define a validity duration for an offer, and set a validity date. We would like to be able
to set either the duration or the date, one impacting the other.

In this case Odoo provides the ability to use an ``inverse`` function::

    from odoo import api, fields, models

    class TestComputed(models.Model):
        _name = "test.computed"

        total = fields.Float(compute="_compute_total", inverse="_inverse_total")
        amount = fields.Float()

        @api.depends("amount")
        def _compute_total(self):
            for record in self:
                record.total = 2.0 * record.amount
        
        def _inverse_total(self):
            for record in self:
                record.amount = record.total / 2.0

An example can be found
`here <https://github.com/odoo/odoo/blob/2ccf0bd0dcb2e232ee894f07f24fdc26c51835f7/addons/crm/models/crm_lead.py#L308-L317>`__.

Note that the ``inverse`` method is only called when saving the record, while the
``compute`` method is called at each change of the dependencies.

.. exercise:: Compute a validity date for offers

    - Add the following fields to the ``estate.property.offer`` model:

    ========================= ========================= =========================
    Field                     Type                      Default
    ========================= ========================= =========================
    validity                  Integer                   7
    date_deadline             Date
    ========================= ========================= =========================

    The ``date_deadline`` is a computed field which is defined as the addition of two fields from
    the offer: the ``create_date`` and the ``validity``. Define the appropriate inverse function
    so that the user can set the date or the validity.

    Tip: the ``create_date`` is only filled in when the record is created. At creation, you will
    need a fallback to prevent crashing.

    - Add the fields in the form and list view as depicted on the second image of the **Goal**.

Additional Information
----------------------

By default, computed fields are **not stored** in the database. A side-effect is that it is **not
possible** to search on the field unless a ``search`` method is defined. This goes beyond the scope
of the the training, so we won't cover it. An example can be found
`here <https://github.com/odoo/odoo/blob/f011c9aacf3a3010c436d4e4f408cd9ae265de1b/addons/event/models/event_event.py#L188>`__.

Another solution is to store the field thanks to the ``store=True`` attribute. While this is
usually convenient, pay attention to the potential computation load added to your model. Lets re-use
our example::

    description = fields.Char(compute="_compute_description", store=True)
    partner_id = fields.Many2one("res.partner")

    @api.depends("partner_id.name")
    def _compute_description(self):
        for record in self:
            record.description = "Test for partner %s" % record.partner_id.name

Every time the partner ``name`` is changed, the ``description`` is automatically recomputed for
**all the records** referring to it! This can quickly be prohibitive to recompute when
millions of records need recomputation.

It is also worth noting that a computed field can depend on another computed field. The ORM is
smart enough to recompute correctly all the dependencies in the right order... sometimes at the
cost of degraded performances.

More generally, performance must always be kept in mind when defining computed fields. The more
complex is your field to compute (e.g. with a lot of dependencies, or when a computed field
depends on other computed fields), the more time it will take to compute. Always take some time to
evaluate the cost of a computated field beforehand: most of the time, it is only when your code
reaches a production server that you realize it slows down a whole process. Not cool :-(

Onchanges
=========

**Reference**: the documentation related to this topic can be found in
:func:`~odoo.api.onchange`:

.. note::

    **Goal**: at the end of this section, enabling the garden will set a default area of 10 and
    an orientation to North. 

    .. image:: compute_onchange/media/onchange.gif
        :align: center
        :alt: Onchange

In our real estate module, we also want to help the user encoding. When the 'garden' field is set,
we want to give a default value for the garden area as well as the orientation. Moreover, when the
'garden' field is unset the garden area is reset to zero and the orientation is removed. In this
case, the value of a given field modifies the value of other fields.

The 'onchange' mechanism provides a way for the client interface to update a
form whenever the user has filled in a value in a field, without saving anything
to the database. To achieve this, we define a method where ``self`` represents
the record in the form view, and decorate it with :func:`~odoo.api.onchange`
to specify on which field it has to be triggered. Any change you make on
``self`` will be reflected on the form::

    from odoo import api, fields, models

    class TestOnchange(models.Model):
        _name = "test.onchange"

        name = fields.Char(string="Name")
        description = fields.Char(string="Description")
        partner_id = fields.Many2one("res.partner", string="Partner")

        @api.onchange("partner_id")
        def _onchange_partner_id(self):
            self.name = "Document for %s" % (self.partner_id.name)
            self.description = "Default description for %s" % (self.partner_id.name)

In this example, changing the partner will reset the name and the description. It is always up to
the user to change the given values later on. Also note that we do not loop on ``self``: this
is because the method is only triggered in a form view, where ``self`` is always a single record.

.. exercise:: Set values to garden area and orientation

    Create an ``onchange`` on the ``estate.property`` model in order to give a value to the
    garden area (10) and orientation (North) when the garden is set. When unset, clean the fields.

Additional Information
----------------------

Onchanges methods can also return a non-blocking warning message
(`example <https://github.com/odoo/odoo/blob/cd9af815ba591935cda367d33a1d090f248dd18d/addons/payment_authorize/models/payment.py#L34-L36>`__).

How to use them?
================

There is no strict rule on the use of computed fields and onchanges.

In many cases, both computed fields and onchanges may be used to achieve the same result. Always
prefer computed fields since they are also triggered outside of the context of a form view. Never
ever use an onchange to add business logic to your model. This is a **very bad** idea since
onchanges are not automatically triggered when creating a record programmatically; they are only
triggered on the form view.

The usual pitfall of computed fields and onchanges is trying to be 'too smart' by adding too much
logic. This can have the opposite result of what was expected: the end user is confused about
all the automation.

Computed fields tend to be easier to debug: such a field is set by a given method, so it's easy to
track when the value is set. Onchanges, on the other hand, may be confusing: it is very difficult to
be sure of the extent of an onchange. Indeed, several onchange methods may set the same fields: it
then becomes difficult to track where a value is coming from.

When using stored computed fields, pay close attention to the dependencies. When computed fields
depend on other computed fields, changing a value can trigger a large number of recomputations.
This leads to bad performances.

In the :ref:`next chapter<howto/rdtraining/actions>`, we'll see how we can trigger some business
logic when clicking on buttons.
