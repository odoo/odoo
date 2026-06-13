# Odoo Coding Conventions

## Models

```python
class MyModel(models.Model):
    _name = 'my.model'          # new model
    _inherit = 'existing.model' # extend in place (no _name) or copy (with new _name)
    _rec_name = 'name'          # set explicitly if display name is not 'name'
    _description = 'My Model'  # required

    # Field naming
    name = fields.Char()
    partner_id = fields.Many2one('res.partner', ondelete='restrict')
    line_ids = fields.One2many('my.model.line', 'model_id')
    tag_ids = fields.Many2many('my.tag')

    # Method prefixes
    def _compute_amount(self):   # compute
    def _onchange_partner(self): # onchange
    def _check_date(self):       # constraint
    def _default_currency(self): # default
```

## Decorators

```python
@api.depends('line_ids.price_unit', 'line_ids.qty')  # required on every compute
def _compute_amount(self):
    ...

@api.onchange('partner_id')  # UI only — does not persist until save
def _onchange_partner(self):
    ...

@api.constrains('date_start', 'date_end')  # runs on save; raise ValidationError to block
def _check_dates(self):
    ...

@api.model  # no recordset; operates on the model class
def create(self, vals):
    ...
```

## Relational field commands (Many2many / One2many writes)

```python
# Replace all records
record.tag_ids = [(6, 0, [id1, id2])]

# Add records
record.tag_ids = [(4, id)]

# Remove a record
record.tag_ids = [(3, id)]

# Create and link
record.tag_ids = [(0, 0, {'name': 'New Tag'})]
```

## Security

Every new `_name` model needs:
1. An entry in `security/ir.model.access.csv`
2. Optionally `ir.rule` records for row-level access

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_my_model_user,my.model user,model_my_model,base.group_user,1,1,1,0
```

## XML IDs

Always prefix with the module name to avoid conflicts:

```xml
<!-- Good -->
<record id="my_module.my_view_form" model="ir.ui.view">

<!-- Bad — will conflict across modules -->
<record id="my_view_form" model="ir.ui.view">
```

## What NOT to do

- Never edit `odoo/` — extend via `_inherit` in `addons/` only
- Never hardcode database IDs — use `env.ref('module.xml_id')`
- Never use `sudo()` without a comment explaining why
- Never declare a task done without a passing test run as evidence
