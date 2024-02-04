Override _get_field_styles() with a dict of fields list per model


.. code-block:: python

    class Base(models.AbstractModel):
        _inherit = "base"

        def _get_field_styles(self):
            res = super()._get_field_styles()
            res["product.product"] = {
                "my-css-class1": ["field1", "field2"],
                "my-css-class2": ["field3"],
            }
            return res
