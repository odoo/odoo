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

