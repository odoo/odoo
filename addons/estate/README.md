# Real Estate: Server Framework 101

This addon follows the [Odoo 20.0 Server framework 101 tutorial](https://www.odoo.com/documentation/20.0/developer/tutorials/server_framework_101.html) one chapter at a time. Each commit contains the completed work for one chapter. Read the chapter, inspect its commit with `git show`, and try the behavior in Odoo before moving to the next commit.

## Chapter 1 - Architecture overview

[Official chapter](https://www.odoo.com/documentation/20.0/developer/tutorials/server_framework_101/01_architecture.html)

Odoo separates what you see in the browser, the Python code that handles business rules, and the PostgreSQL database that stores records. An addon brings related pieces together. Its models describe business data, views describe how that data appears, and XML or CSV files can create menus, permissions, and other records.

This first commit contains only this README. Before creating the addon, it helps to know where each part of the real estate application belongs and why installing an addon affects a particular database.

**Try it:** Find an existing addon in the repository. Locate its manifest, a model file, and a view file. Decide which of those would store a property's price and which would display it.

## Chapter 2 - A new application

[Official chapter](https://www.odoo.com/documentation/20.0/developer/tutorials/server_framework_101/02_newapp.html)

An Odoo addon needs a Python package and a manifest before Odoo can discover it. This chapter adds `__init__.py` and `__manifest__.py` to `estate`. The manifest gives the addon a name, declares its dependency on `base`, and sets `application=True` so it appears under the Apps filter.

The addon is an empty shell at this point. It can be installed, but it has no model or menu yet. That separation makes it easier to see what the manifest does before business features are added.

**Try it:** Enable developer mode, update the Apps list, and install Real Estate. Notice that the app appears in the list even though it has no main menu yet.

## Chapter 3 - Models and basic fields

[Official chapter](https://www.odoo.com/documentation/20.0/developer/tutorials/server_framework_101/03_basicmodel.html)

The new `estate.property` model gives the application somewhere to store property records. Its Python class defines fields for the name, description, postcode, availability, prices, rooms, area, and garden details. The ORM maps the model to a PostgreSQL table named `estate_property`.

`name` and `expected_price` are required because a useful property record needs both. `garden_orientation` stores one of four keys while showing readable labels in the interface. Odoo also adds fields such as `id` and `create_date` automatically; they do not need declarations in our class.

**Try it:** Upgrade `estate` and inspect the `estate_property` table. Compare its columns with the Python fields, then find an automatic field that was not declared in `estate_property.py`.

## Chapter 4 - Security: a brief introduction

[Official chapter](https://www.odoo.com/documentation/20.0/developer/tutorials/server_framework_101/04_securityintro.html)

A model does not become available to every user merely because it exists. This chapter adds an access row for `base.group_user`, granting internal users create, read, update, and delete access to properties. The manifest loads that row when the addon is installed or upgraded.

The tutorial text shows the older `ir.model.access.csv` layout. This Odoo 20 checkout uses `security/ir.access.csv`, where the `operation` column lists the granted operations. The underlying idea is the same: permissions are data loaded by the module, and a menu alone does not grant model access.

**Try it:** Upgrade `estate` and check that its missing-access warning is gone. Compare property access for an internal user with access for a user outside that group.

## Chapter 5 - Finally, some UI to play with

[Official chapter](https://www.odoo.com/documentation/20.0/developer/tutorials/server_framework_101/05_firstui.html)

A window action connects a menu to `estate.property`. The new menu path is Real Estate > Advertisements > Properties. Odoo can now open its generated list and form views, so you can create a property before any custom views exist.

The model also gains useful defaults and lifecycle fields. New properties start with two bedrooms, an availability date three months ahead, `active=True`, and state New. Availability and selling price are not copied when a property is duplicated. Selling price is read-only in the form because accepting an offer will set it later.

**Try it:** Create and duplicate a property. Compare their availability dates and selling prices, then archive one property and look for it in the normal list.

## Chapter 6 - Basic views

[Official chapter](https://www.odoo.com/documentation/20.0/developer/tutorials/server_framework_101/06_basicviews.html)

Generated views expose fields, but they do not organize the application around a user's task. This chapter adds a property list with the most useful columns, a form grouped by purpose, and a search view for finding records. These XML views change how records appear without changing their database fields.

The Available filter selects properties in New or Offer Received state. Group By Postcode rearranges the results without modifying any record. Search domains choose records; grouping context changes their presentation.

**Try it:** Create properties in two postcodes. Search by name, apply Available, and group by postcode. Remove a field from a view in your local experiment and check whether its database column still exists.

## Chapter 7 - Relations between models

[Official chapter](https://www.odoo.com/documentation/20.0/developer/tutorials/server_framework_101/07_relations.html)

Properties now connect to property types, tags, buyers, salespeople, and offers. A property has one type (`Many2one`), many tags (`Many2many`), and many offers (`One2many`). An offer points back to exactly one property through its required `property_id` field. Reusing `res.partner` for buyers and `res.users` for salespeople avoids creating duplicate contact and user models.

The new type and tag models have configuration menus and access rights. Offers have views and access rights but no separate menu because they are entered from a property's Offers tab. The salesperson defaults to the current user, while the buyer is left blank when a property is duplicated.

**Try it:** Create a type and a tag, assign them to a property, and add an offer from its Offers tab. Inspect the offer's `property_id` to see how Odoo connected the records.

