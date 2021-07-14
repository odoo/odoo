================
 Attachment Url
================

Installation
============

* `Install <https://odoo-development.readthedocs.io/en/latest/odoo/usage/install-module.html>`__ this module in a usual way

Usage
=====

* Set an avatar for the current user
* `Log in as superuser <https://odoo-development.readthedocs.io/en/latest/odoo/usage/login-as-superuser.html>`__
* Go to Settings >> Technical >> Database Structure >> Attachments
* Below "Search" field click Filters >> Add custom filter >> "Resource field" "is equal to" "image_128"
* Scroll down and find the avatar you have set. Click on it.
* Click on "Edit"
* To URL field paste url to any picture on external resource. Keep field **Type** equal to *File*.
* Click on "Save" and reload the page
* RESULT: you will see that the avatar of the user has been changed to that
  pasted picture. If you open image address in a new tab, you will be redirected
  to the external url.

ir_attachment_url_fields context
--------------------------------

In order to store urls instead of binary data in binary fields, you can use ``ir_attachment_url_fields`` context.
For example, you need to create ``ir.ui.menu`` record which has ``web_icon_data`` fields, defined as `Binary field <https://github.com/odoo/odoo/blob/b29ac84fd55923abf582cdee39cb32bacda3eec9/odoo/addons/base/models/ir_ui_menu.py#L45>`__.
To store url to ``web_icon_data`` field you need to define context ``ir_attachment_url_fields="ir.ui.menu.web_icon_data"`` and set value of the field. See `test cases <../tests/test_attachment_fields.py>`__ as detailed examples.

In order to store multiple fields as urls, define context like this ``ir_attachment_url_fields="model.name.field1,another.model.name.field2"``.
