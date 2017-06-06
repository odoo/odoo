# download_action
[![Build Status](https://drone.io/bitbucket.org/naglis/download_action/status.png)](https://drone.io/bitbucket.org/naglis/download_action/latest)

File download action module for Odoo.

## Requirements

- Odoo v8

## Usage

Add a button, for example:
```xml
<?xml version="1.0" encoding="utf-8"?>
<openerp>
    <data>
    <record id="view_order_form_demo_download" model="ir.ui.view">
            <field name="name">sale.order.form.download_action_demo</field>
            <field name="model">sale.order</field>
            <field name="inherit_id" ref="sale.view_order_form"/>
            <field name="priority">1000</field>
            <field name="arch" type="xml">
                <xpath expr="/form/header/button[@name='print_quotation']" position="after">
                    <button name="act_download" string="Download demo" class="oe_highlight" type="object"/>
                </xpath>
            </field>
        </record>
    </data>
</openerp>
```
and write a function, which returns an action `dict`:

If you want to return a generated file:
```python

@download_file
def act_download(self, cr, uid, ids, *args, **kwargs):

    import io
    import os

    bio = io.BytesIO()
    bio.write(os.urandom(1024 * 1024)) # 1MB

    return {
        'type': 'ir.actions.download',
        'filename': 'test.bin',
        'file': bio.getvalue()
    }
```

or, if you want to download a file which is stored in a binary field in the
database:

```python

def act_download(self, cr, uid, ids, *args, **kwargs):

    return {
        'type': 'ir.actions.download',
        'model': 'ir.attachment',
        'field': 'datas',
        'id': '4',
        'filename': 'attachment.jpg',
    }
```

Note that the `@download_file` decorator is only required when you return the
file within the dict.

