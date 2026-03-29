For regular usage, see Usage below. This section is to clarify optional
functionality to developers.

To configure a model to use the Many2one style search field, make the
model inherit from \`date.range.search.mixin\`:

```
class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "date.range.search.mixin"]
```

This will make a Period field show up in the search view:

> ![search_view](https://raw.githubusercontent.com/OCA/server-ux/18.0/date_range/static/description/date_range_many2one_search_field.png)

By default, the mixin works on the date field. If you want the mixin to
work on a field with a different name, you can set a property on your
model:

```
_date_range_search_field = "invoice_date"
```
