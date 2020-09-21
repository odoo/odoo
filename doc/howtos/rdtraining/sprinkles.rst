.. _howto/rdtraining/sprinkles:

================
Add The Spinkles
================

Our real estate module now makes sense from a business persective: we created
:ref:`specific views <howto/rdtraining/basicviews>`, added several
:ref:`action buttons <howto/rdtraining/actions>` and
:ref:`constraints <howto/rdtraining/constraints>`. However, our user interface is still a bit
rough. We would like to add some colors in the list views or make some fields and buttons disappear
conditionally. For example, the 'Sold' and 'Cancel' button should disappear when the property
is sold or canceled since it is not allowed to change the state in this case.

This chapter covers a very small subset of what can be done in the views. Do not hesitate to
read the reference documentation for a more complete insight.

**Reference**: the documentation related to this chapter can be found in
:ref:`reference/views`.

Inline Views
============

.. note::

    **Goal**: at the end of this section, a specific list of properties is added in the property
    type view:

    .. image:: sprinkles/media/inline_view.png
      :align: center
      :alt: Inline list view

In the real estate module, we added the list of offers on a property. We simply added the field
``offer_ids`` with:

.. code-block:: xml

    <field name="offer_ids"/>

The field uses the specific view for ``estate.property.offer``. In some cases, we want to define
a specific list view which is only used in the context of a form view. For example, we would like
to display the list of properties linked to a property type. However, we only want to display 3
fields for clarity: name, expected price, state.

To do this, we can define *inline* list views: an inline list view is defined directly inside
a form view. For example:

.. code-block:: python

    from odoo import fields, models

    class TestModel(models.Model):
        _name = "test.model"
        _description = "Test Model"

        description = fields.Char()
        line_ids = fields.One2many("test.model.line", "model_id")


    class TestModelLine(models.Model):
        _name = "test.model.line"
        _description = "Test Model Line"

        model_id = fields.Many2one("test.model")
        field_1 = fields.Char()
        field_2 = fields.Char()
        field_3 = fields.Char()

.. code-block:: xml

    <form>
        <field name="description"/>
        <field name="line_ids">
            <tree>
                <field name="field_1"/>
                <field name="field_2"/>
            </tree>
        </field>
    </form>

In the form view of the ``test.model``, we define a specific list view for ``test.model.line``
with fields ``field_1`` and ``field_2``.

An example can be found
`here <https://github.com/odoo/odoo/blob/0e12fa135882cd5095dbf15fe2f64231c6a84336/addons/event/views/event_tag_views.xml#L27-L33>`__.

.. exercise:: Add an inline list view

    - Add the ``One2many`` field ``property_ids`` on the ``estate.property.type`` model.
    - Add the field in the ``estate.property.type`` form view as depicted in the **Goal** of the
      section.

Widgets
=======

**Reference**: the documentation related to this section can be found in
:ref:`reference/js/widgets`.

.. note::

    **Goal**: at the end of this section, the state of the property is displayed thanks to a
    specific widget:

    .. image:: sprinkles/media/widget.png
      :align: center
      :alt: Statusbar widget

    Four states are displayed: New, Offer Received, Offer Accepted and Sold.

When we added fields our models, we (almost) never had to worry about how the field would look like
in the user interface. For example, a date picker is provided for a ``Date`` field, or a
``One2many`` field is automatically displayed as a list. Odoo chooses the right 'widget' depending
on the field type.

However, in some cases, we want a specific representation of a field which can be done thanks to
the ``widget`` attribute. We already used it for the ``tag_ids`` field when we used the
``widget="many2many_tags"`` attribute. In fact, when we don't use it, the field is displayed as a
list.

Each field type has a set of widgets which can be used to fine tune its display. Some widgets also
take extra options. An exhaustive list can be found in :ref:`reference/js/widgets`.

.. exercise:: Use the status bar widget

    Use the ``statusbar`` widget in order to display the ``state`` of the ``estate.property`` as
    depicted in the **Goal** of the section.

    Tip: a simple example can be found
    `here <https://github.com/odoo/odoo/blob/0e12fa135882cd5095dbf15fe2f64231c6a84336/addons/account/views/account_bank_statement_views.xml#L136>`__.

List Order
==========

**Reference**: the documentation related to this section can be found in
:ref:`reference/orm/models`.

.. note::

    **Goal**: at the end of this section, all lists are displayed by default in a deterministic
    order. Property types can be ordered manually.

During the various exercises, we created several list views. However, at no point we specified
in which order the records had to be listed by default. This is of major importance in many business
cases. For example, in our real estate module we want to display the highest offers on top of the
list.

Model
-----

Odoo provides several ways to set a default order. The most common way to do it is to define
the ``_order`` attribute directly on the model. This way, the retrieved records will follow
a deterministic order which will be consistent in all views, but also when records are searched
programmatically. By default there is no order specified, therefore the records will be
retrieved in a non-deterministic order depending on PostgreSQL.

The ``_order`` attribute takes a string containing a list of fields which will be used for sorting.
It will be converted in an order_by_ clause in SQL. For example:

.. code-block:: python

    from odoo import fields, models

    class TestModel(models.Model):
        _name = "test.model"
        _description = "Test Model"
        _order = "id desc"

        description = fields.Char()

Our records are ordered by descending ``id``, meaning the highest comes first.

.. exercise:: Model ordering

    Define the following orders on the models:

    =================================== ===================================
    Model                               Order
    =================================== ===================================
    ``estate.property``                 Descending ID
    ``estate.property.offer``           Descending Price
    ``estate.property.tag``             Name
    ``estate.property.type``            Name
    =================================== ===================================

View
----

Ordering is possible at the model level: this has the advantage of a consistent order everywhere
a list of records is retrieved. However, it is also possible to define a specific order directly
on a view thanks to the ``default_order`` attribute
(`example <https://github.com/odoo/odoo/blob/892dd6860733c46caf379fd36f57219082331b66/addons/crm/report/crm_activity_report_views.xml#L30>`__).

Manual
------

Both model and view ordering allow flexibility when sorting records. But there is still one case
we need to cover: the manual ordering. A user may want to sort records depending on the business
logic. For example, In our real estate module we would like to sort the property types manually.
Indeed, it is useful to have the most used types appear at the top of the list. If our real estate
agency mainly sells houses, it is more convenient to have 'House' appear before 'Apartment'.

To do so, a ``sequence`` field is used in combination with the ``handle`` widget. Obviously,
the ``sequence`` field must be the first field in the ``_order`` attribute.

.. exercise:: Manual ordering

    - Add the following field:

    =================================== ======================= =======================
    Model                               Field                   Type
    =================================== ======================= =======================
    ``estate.property.type``            Sequence                Integer
    =================================== ======================= =======================

    - Add the sequence to the ``estate.property.type`` list view with the right widget.

    Tip: you can find an example here:
    `model <https://github.com/odoo/odoo/blob/892dd6860733c46caf379fd36f57219082331b66/addons/crm/models/crm_stage.py#L36>`__
    and
    `view <https://github.com/odoo/odoo/blob/892dd6860733c46caf379fd36f57219082331b66/addons/crm/views/crm_stage_views.xml#L23>`__.

Attributes and options
======================

It would be prohibitive to detail all the available features which allow fine tuning the look of a
view. Therefore, we'll only stick to the most common ones.

Form
----

.. note::

    **Goal**: at the end of this section, the property form view has:
    - Conditional display of buttons and fields
    - Tag colors

    .. image:: sprinkles/media/form.gif
      :align: center
      :alt: Form view with sprinkles

In our real estate module, we want to modify the behavior of some fields. For example, we don't
want to be able to create or edit a property type from the form view. In fact, we expect the
types to be handled in their appropriate menu. Moreover, we want to give tags a color. Several field
widgets take the ``options`` attribute in to customize their behavior.

.. exercise:: Widget options

    - Add the appropriate option to the ``property_type_id`` field to prevent the creation and the
      edition of a property type from the property form view. Have a look at the
      :ref:`Many2one widget documentation <reference/js/widgets>` for more info.

    - Add the following field:

    =================================== ======================= =======================
    Model                               Field                   Type
    =================================== ======================= =======================
    ``estate.property.tag``             Color                   Integer
    =================================== ======================= =======================

    Then, add the appropriate option to the ``tag_ids`` field to add a color picker on the tags.
    Have a look at the :ref:`FieldMany2ManyTags widget documentation <reference/js/widgets>`
    for more info.

In the :ref:`howto/rdtraining/firstui` chapter, we saw that reserved fields was used for
specific behaviors. For example, the ``active`` field is used to automatically filter out
inactive records. We added the ``state`` as a reserved field as well. It's now time to use it!
A ``state`` field is used in combination with a ``states`` attribute in the view to display
buttons conditionally.

.. exercise:: Conditional display of buttons

    Use the ``states`` attribute to display the header buttons conditionally as depicted
    in the **Goal**.

    Tip: do not hesitate to search for ``states=`` in the Odoo XML files to get some examples.

More generally, it is possible to make a field ``invisible``, ``readonly`` or ``required`` based
on the value of other fields thanks to the ``attrs`` attribute. Note that ``invisible`` also applies
to other elements of the view such as ``buttons`` or ``group``.

The ``attrs`` is a dictionary with the property as a key and a domain as a value. The domain gives
the conditon in which the property applies. For example:

.. code-block:: xml

    <form>
        <field name="description" attrs="{'invisible': [('is_partner', '=', False)]}"/>
        <field name="is_partner" invisible="1"/>
    </form>

It means that the ``description`` field is invisible when ``is_partner`` is ``False``. It is
important to note that a field used in an ``attrs`` **must** be present in the view. If it
should not be displayed to the user, we can use the ``invisible`` attribute to hide it.

.. exercise:: Use of ``attrs``

    - Make the garden area and orientation invisible in the ``estate.property`` form view when
      there is no garden.
    - Make the 'Accept' and 'Refuse' button invisible once the offer state is set.
    - Do not allow adding an offer when the property state is 'Offer Accepted', 'Sold' or
      'Canceled'. To do this, use the ``readonly`` ``attrs``.

.. warning::

    Using a (conditional) ``readonly`` attribute in the view can be useful to prevent encoding
    errors, but keep in mind that it doesn't provide any level of security! There is no check done
    server-side, therefore it's always possible to write on the field through RPC call.

List
----

.. note::

    **Goal**: at the end of this section, the property and offer list views have color decorations.
    Moreover, offers and tags are editable directly in the list, and the availability date is
    hidden by default.

    .. image:: sprinkles/media/decoration.png
      :align: center
      :alt: List view with decorations and optional field

    .. image:: sprinkles/media/editable_list.gif
      :align: center
      :alt: Editable list

In case the model has only a few fields, it can be useful to edit records directly through the list
view and not open the form view. In the real estate example, there is no need to open a form view
to add an offer or create a new tag. It can be achieved thanks to the ``editable`` attribute.

.. exercise:: Make list views editable

    Make the ``estate.property.offer`` and ``estate.property.tag`` list views editable.

On the other hand, when a model has a lot of fields it can be tempting to add too many fields in the
list view, making it unclear. An alternative method is to add the fields, but make them optionally
hidden. It can be achieved thanks to the ``optional`` attribute.

.. exercise:: Make a field optional

    Make the field ``date_availability`` on the ``estate.property`` list view optional and hidden by
    default.

Finally, color codes are useful to visually emphasize records. For example, in the real estate
module we would like refused offers in red and the accepted offer in green. It can be achieved
thanks to the ``decoration-{$name}`` attribute (see :ref:`reference/js/widgets` for a
complete list):

.. code-block:: xml

    <tree decoration-success="is_partner==True">
        <field name="name">
        <field name="is_partner" invisible="1">
    </tree>

The records where ``is_partner`` is ``True`` will be displayed in green.

.. exercise:: Add some decoration

    On the ``estate.property`` list view:

    - Properties with an offer received are green
    - Properties with an offer accepted are green and bold
    - Properties sold are muted

    On the ``estate.property.offer`` list view:

    - Refused offers are red
    - Accepted offers are green
    - The state should not be visible anymore

    Tips:
    - keep in mind that **all** fields used in attributes must be in the view!
    - if you want to test the color of the "Offer Received" and "Offer Accepted" states, add the
    field in the form view and change it manually (we'll implement this later). 

Search
------

**Reference**: the documentation related to this section can be found in
:ref:`reference/views/search` and :ref:`reference/views/search/defaults`.

.. note::

    **Goal**: at the end of this section, the available properties are filtered by default.
    Moreover, searching on the living area returns results where the area is larger than the given
    number.

    .. image:: sprinkles/media/search.gif
      :align: center
      :alt: Default filters and domains

Last but not least, there are some tweaks we would like to apply when searching. First of all, we
want to have our 'Available' filter used by default when we access the properties. To do so, we
need to use the ``search_default_{$name}`` action context, where ``{$name}`` is the filter name.
It means that we can define which filter must be activated by default at the action level.

Here is an example of
`action <https://github.com/odoo/odoo/blob/6decc32a889b46947db6dd4d42ef995935894a2a/addons/crm/report/crm_opportunity_report_views.xml#L115>`__
with the
`corresponding filter <https://github.com/odoo/odoo/blob/6decc32a889b46947db6dd4d42ef995935894a2a/addons/crm/report/crm_opportunity_report_views.xml#L68>`__.

.. exercise:: Add a default filter

    Make the 'Available' filter selected by default on the ``estate.property`` action.

Another useful improvement in our module would be to be able to search efficiently by living area.
In practice, a user will want to search for properties of 'at least' the given area. There is no
real use case where one would want to find a property of an exact living area. It is always
possible to make a custom search, but that's not convenient. 

Search view ``<field>`` elements can have a ``filter_domain`` that overrides
the domain generated for searching on the given field. In the given domain,
``self`` represents the value entered by the user. In the example below, it is
used to search on both fields ``name`` and ``description``.

.. code-block:: xml

    <search string="Test">
        <field name="description" string="Name and description"
               filter_domain="['|', ('name', 'ilike', self), ('description', 'ilike', self)]"/>
        </group>
    </search>

.. exercise:: Change the living area search

    Add a ``filter_domain`` on the living area to include properties with an area larger than the
    given value.

Stat Buttons
============

.. note::

    **Goal**: at the end of this section, a stat button on the property type which gives the list
    of all offers related to properties of the given type.

    .. image:: sprinkles/media/stat_button.gif
      :align: center
      :alt: Stat button

If you already used some functional modules in Odoo, you probably already encountered a 'stat
button'. These buttons are displayed on the top right of a form view and give a quick access to
linked documents. In our real estate module, we would like to have a quick link to the offers
related to a given property type, as depicted in the **Goal** of the section.

At this point of the tutorial we have seen mostly all the concepts to be able to do it. However,
there is not a single solution, and it can still be confusing if you don't know where to start from.
We'll describe a step-by-step solution in the exercise. It can always be useful to find some
examples in the Odoo codebase by looking for ``oe_stat_button``.

The following exercise might be a bit more difficult than the previous ones since it assumes you
are able to search examples in the source code on your own. If you are stuck, there is probably
someone close to you who can help you ;-)

The exercise introduces the concept of :ref:`reference/fields/related`. The easiest way to
understand it is to consider it as a specific case of a computed field. The following definition
of the ``description`` field:

.. code-block:: python

        ...

        partner_id = fields.Many2one("res.partner", string="Partner")
        description = fields.Char(related="partner_id.name")

is equivalent to:

.. code-block:: python

        ...

        partner_id = fields.Many2one("res.partner", string="Partner")
        description = fields.Char(compute="_compute_description")

        @api.depends("partner_id.name")
        def _compute_description(self):
            for record in self:
                record.description = record.partner_id.name

Every time the partner name is changed, the description is modified.

.. exercise:: Add a stat button on property type

    - Add the field ``property_type_id`` on ``estate.property.offer``. We can define it as a
      related field on ``property_id.property_type_id`` and set as stored.
      
    Thanks to this field, an offer will be linked to a property type when created. You can add
    the field to the list view of the offers to make sure it works.

    - Add the field ``offer_ids`` on ``estate.property.type`` which is the One2many inverse of
      the field defined at the previous step.

    - Add the field ``offer_count`` on ``estate.property.type``. It is a computed field that counts
      the number of offers for a given property type (use ``offer_ids`` to do so).
    
    At this point, you have all the information necessary to know how many offers are linked to
    a property type. In doubt, add ``offer_ids`` and ``offer_count`` directly in the view.
    The next step is to display the list when clicking on the stat button.

    - Create a stat button on ``estate.property.type`` pointing to the ``estate.property.offer``
      action. It means you should use the ``type="action"`` attribute (go back to the end of
      :ref:`howto/rdtraining/actions` for a refresh).

    At this point, clicking on the stat button should display all offers. We need to filter out the
    offers.

    - On the ``estate.property.offer`` action, add a domain defining that the ``property_type_id``
      should be equal to the ``active_id`` (= the current record,
      `example <https://github.com/odoo/odoo/blob/df37ce50e847e3489eb43d1ef6fc1bac6d6af333/addons/event/views/event_views.xml#L162>`__)

Looking good? If not, no worry, the :ref:`next chapter <howto/rdtraining/inheritance>` doesn't
require stat buttons ;-)

.. _order_by:
    https://www.postgresql.org/docs/current/queries-order.html
