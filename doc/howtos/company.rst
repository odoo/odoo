:banner: banners/company.jpg

.. _reference/howtos/company:

========================
Multi-company Guidelines
========================

.. warning::

    This tutorial requires good knowledge of Odoo.
    Please refer to the :ref:`basic tutorial <howto/base>` first if needed.

As of version 13.0, a user can be logged in multiple companies at once. This allows the user to
access information from multiple companies but also to create/edit records in a multi-company
environment.

If not handled correctly, it may be the source of a lot of inconsistent multi-company behaviors.
For instance, a user logged in both companies A and B could create a sales order in company A and
add products belonging to company B to it. It is only when the user will log out from company B that
access errors will occur for the sales order.

To correctly manage multi-company behaviors, Odoo's ORM provides multiple features:

- :ref:`Company-dependent fields <howto/company/company_dependent>`
- :ref:`Multi-company consistency <howto/company/check_company>`
- :ref:`Default company <howto/company/default_company>`
- :ref:`Views <howto/company/views>`
- :ref:`Security rules <howto/company/security>`

.. _howto/company/company_dependent:

Company-dependent fields
------------------------

When a record is available from multiple companies, we must expect that different values will be
assigned to a given field depending on the company from which the value is set.

For the field of a same record to support several values, it must be defined with the attribute
`company_dependent` set to `True`.

.. code-block:: python

   from odoo import api, fields, models

   class Record(models.Model):
       _name = 'record.public'

       info = fields.Text()
       company_info = fields.Text(company_dependent=True)
       display_info = fields.Text(string='Infos', compute='_compute_display_info')

       @api.depends_context('force_company')
       def _compute_display_info(self):
           for record in self:
               record.display_info = record.info + record.company_info

.. note:: The `_compute_display_info` method is decorated with `depends_context('force_company')`
          (see :attr:`~odoo.api.depends_context`) to ensure that the computed field is recomputed
          depending on the forced/current company (`force_company` context key set, or
          `self.env.company`).

When a company-dependent field is read, the current company is used to retrieve its value. In other
words, if a user is logged in companies A and B with A as main company and creates a record for
company B, the values of company-dependent fields will be that of company A.

To read the values of company-dependent fields set from another company than the current one, the
context key `force_company` must be set to the ID of the desired company.

.. code-block:: python

   # Accessed as main company (self.env.company)
   val = record.company_dependent_field

   # Accessed as desired company (company_B)
   val = record.with_context(force_company=company_B.id).company_dependent_field


.. _howto/company/check_company:

Multi-company consistency
-------------------------

When a record is made shareable between several companies by the mean of a `company_id` field, we
must take care that it cannot be linked to the record of another company through a relational field.
For instance, we do not want to have a sales order and its invoice belonging to different companies.

To ensure this multi-company consistency, you must:

* Set the class attribute `_check_company_auto` to `True`.
* Define relational fields with the attribute `check_company` set to `True` if their model has a
  `company_id` field.

On each :meth:`~odoo.models.Model.create` and :meth:`~odoo.models.Model.write`, automatic checks
will be triggered to ensure the multi-company consistency of the record.

.. code-block:: python

   from odoo import fields, models

   class Record(models.Model):
       _name = 'record.shareable'
       _check_company_auto = True

       company_id = fields.Many2one('res.company')
       other_record_id = fields.Many2one('other.record', check_company=True)

.. note:: The field `company_id` must not be defined with `check_company=True`.

.. currentmodule:: odoo.models
.. automethod:: Model._check_company

.. warning:: The `check_company` feature performs a strict check ! It means that if a record has no
             `company_id` (i.e. the field is not required), it cannot be linked to a record whose
             `company_id` is set.

.. note::

    When no domain is defined on the field and `check_company` is set to `True`, a default domain is
    added: `['|', '('company_id', '=', False), ('company_id', '=', company_id)]`

.. _howto/company/default_company:

Default company
---------------

When the field `company_id` is made required on a model, a good practice is to set a default
company. It eases the setup flow for the user or even guarantees its validity when the company is
hidden from the view. Indeed, the company is usually hidden if the user does not have access to
multiple companies (i.e. when the user does not have the group `base.group_multi_company`).

.. code-block:: python

   from odoo import api, fields, models

   class Record(models.Model):
       _name = 'record.restricted'
       _check_company_auto = True

       company_id = fields.Many2one(
           'res.company', required=True, default=lambda self: self.env.company
       )
       other_record_id = fields.Many2one('other.record', check_company=True)


.. _howto/company/views:

Views
-----

As stated in :ref:`above <howto/company/default_company>`, the company is usually hidden
from the view if the user does not have access to multiple companies. This is tested with the group
`base.group_multi_company`.

.. code-block:: xml

   <record model="ir.ui.view" id="record_form_view">
       <field name="name">record.restricted.form</field>
       <field name="model">record.restricted</field>
       <field name="arch" type="xml">
           <form>
               <sheet>
                   <group>
                       <group>
                           <field name="company_id" groups="base.group_multi_company"/>
                           <field name="other_record_id"/>
                       </group>
                   </group>
               </sheet>
           </form>
       </field>
   </record>


.. _howto/company/security:

Security rules
--------------

When working with records shared across companies or restricted to a single company, we must take
care that a user does not have access to records belonging to other companies.

This is achieved with security rules based on `company_ids`, which contains the current companies of
the user (the companies the user checked in the multi-company widget).

.. code-block:: xml

    <!-- Shareable Records -->
    <record model="ir.rule" id="record_shared_company_rule">
        <field name="name">Shared Record: multi-company</field>
        <field name="model_id" ref="model_record_shared"/>
        <field name="global" eval="True"/>
        <field name="domain_force">
            ['|', ('company_id', '=', False), ('company_id', 'in', company_ids)]
        </field>
    </record>

.. code-block:: xml

    <!-- Company-restricted Records -->
    <record model="ir.rule" id="record_restricted_company_rule">
        <field name="name">Restricted Record: multi-company</field>
        <field name="model_id" ref="model_record_restricted"/>
        <field name="global" eval="True"/>
        <field name="domain_force">
            [('company_id', 'in', company_ids)]
        </field>
    </record>

.. todo:: check_company on company_dependent fields.
