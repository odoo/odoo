./odoo-bin -d db1 -u base 

./odoo-bin -c ./odoo.conf

2026-05-21 10:17:01,957 220645 WARNING db4 odoo.modules.loading: The models ['estate_test_model', 'estate.property'] have no access rules in module estate, consider adding some, like:
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink


./odoo-bin -c ./odoo.conf --dev=all -i base

<!-- auto reload xml -->
./odoo-bin -c ./odoo.conf -u estate --dev xml


# Naming

- Model name: estate.property
- Table name: estate_property
- Model reference ID (in security file): model_estate_property

Notes: for the model reference ID in security file, the model_id:id column requires an XML ID, is must have the prefix model_ with the model name in underscore

# Loading modules

[ Your Module Folder ]
   │
   ├──► __manifest__.py  ───► Talks to ODOO  (Views, Security, Module Metadata)
   │
   └──► __init__.py      ───► Talks to PYTHON (Loads the actual backend Python code)

---
**`index=True`** — creates a database index on the column, making searches/filters on that field faster. Useful for fields you frequently search or filter by (like salesperson).

**`tracking=True`** — logs changes to the field in the record's chatter (message log). Every time the value changes, Odoo records who changed it, when, and from/to what value. Requires the model to inherit `mail.thread`.

```python
class EstatePropertyModel(models.Model):
    _name = 'estate.property'
    _inherit = ['mail.thread']  # required for tracking to work
    ...
    user_id = fields.Many2one('res.users', string='Salesperson', index=True, tracking=True)
```

Without `_inherit = ['mail.thread']`, `tracking=True` is silently ignored.


- where followers are added to the mails before sending?

- By convention, many2many fields have the _ids suffix. This means that several taxes can be added to our test model. It behaves as a list of records, meaning that accessing the data must be done in a loop

- A list of records is known as a recordset, i.e. an ordered collection of records. It supports standard Python operations on collections, such as len() and iter(), plus extra set operations like recs1 | recs2.