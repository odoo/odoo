This module is an abstract module. You can configure Barcode Rule, but to
enable this feature, you need to install an extra module for a given model.
This repository provide 'barcodes_generator_product' and
'barcodes_generator_partner' module to generate barcode for product or partner
model.

Alternatively, you can develop a custom module for a custom model. See
'Inheritance' parts.

If you want to generate barcode for another model, you can create a custom
module that depend on 'barcodes_generator_abstract' and inherit your model
like that:

.. code::

  class MyModel(models.Model):
      _name = 'my.model'
      _inherit = ['my.model', 'barcode.generate.mixin']

  class barcode_rule(models.Model):
      _inherit = 'barcode.rule'

      generate_model = fields.Selection(selection_add=[('my.model', 'My Model')])

Eventually, you should inherit your model view adding buttons and fields.

Note
~~~~

Your model should have a field 'barcode' defined.
