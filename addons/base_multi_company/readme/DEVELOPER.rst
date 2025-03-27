Implementation
~~~~~~~~~~~~~~

Multi Company Abstract
----------------------

The `multi.company.abstract` model is meant to be inherited by any model that
wants to implement multi-company functionality. The logic does not require a
pre-existing company field on the inheriting model, but will not be affected
if one does exist.

When inheriting the `multi.company.abstract` model, you must take care that
it is the first model listed in the `_inherit` array

.. code-block:: python

   class ProductTemplate(models.Model):
       _inherit = ["multi.company.abstract", "product.template"]
       _name = "product.template"
       _description = "Product Template (Multi-Company)"

The following fields are provided by `multi.company.abstract`:

* `company_ids` - All of the companies that this record belongs to. This is a
  special `res.company.assignment` view, which allows for the circumvention of
  standard cross-company security policies. These policies would normally
  restrict a user from seeing another company unless it is currently operating
  under that company. Be aware of apples to oranges issues when comparing the
  records from this field against actual company records.
* `company_id` - Passes through a singleton company based on the current user,
  and the allowed companies for the record.
* `no_company_ids` - As there is a limitation in Odoo ORM to get real False values
  in Many2many fields (solved on 2022-03-23 https://github.com/odoo/odoo/pull/81344).

Hooks
-----

A generic `post_init_hook` and `uninstall_hook` is provided, which will alter
a pre-existing single-company security rule to be multi-company aware.

These hooks will unfortunately not work in every circumstance, but they cut out
significant boilerplate when relevant.

.. code-block:: python

   import logging

   _logger = logging.getLogger(__name__)

   try:
       from odoo.addons.base_multi_company import hooks
   except ImportError:
       _logger.info('Cannot find `base_multi_company` module in addons path.')


   def post_init_hook(cr, registry):
       hooks.post_init_hook(
           cr,
           'product.product_comp_rule',
           'product.template',
       )


   def uninstall_hook(cr, registry):
       hooks.uninstall_hook(
           cr,
           'product.product_comp_rule',
       )

A module implementing these hooks would need to first identify the proper rule
for the record (`product.product_comp_rule` in the above example).
