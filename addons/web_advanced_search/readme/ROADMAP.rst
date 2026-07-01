Improvements to the ``domain`` widget, not exclusively related to this addon:

* Use relational widgets when filtering a relational field
* Allow to filter field names

Improvements to the search view in this addon:

* Use widgets ``one2many_tags`` when searching ``one2many`` fields
* Use widgets ``many2many_tags`` when searching ``many2many`` fields
* Allow to edit current full search using the advanced domain editor

Issues:

* Grouped totals can show incorrect values. See https://github.com/odoo/odoo/issues/47950
