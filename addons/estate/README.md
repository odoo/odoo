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

## Chapter 8 - Computed fields and onchanges

[Official chapter](https://www.odoo.com/documentation/20.0/developer/tutorials/server_framework_101/08_compute_onchange.html)

A property's total area and best offer can be calculated from information already stored in Odoo. In this chapter, `total_area` adds the living and garden areas, while `best_price` selects the highest offer. `@api.depends` tells Odoo which changes require those values to be recalculated.

Offers also gain a validity period and a deadline. The deadline is calculated from the creation date and validity; an inverse method lets you edit the deadline and have Odoo update the validity instead. For a new offer without a creation date yet, the calculation starts from today.

The garden onchange fills in an area of 10 and a North orientation when Garden is selected, then clears them when it is deselected. This helper runs in the form. The computed fields also work when records are changed through code.

**Try it:** Change a property's living area, add two offers, and edit an offer's deadline. Observe which other values change.

## Chapter 9 - Ready for some action?

[Official chapter](https://www.odoo.com/documentation/20.0/developer/tutorials/server_framework_101/09_actions.html)

Buttons can call public model methods through `type="object"`. Property actions now mark a property Sold or Cancelled, and offer actions accept or refuse an offer. These actions make the workflow more than a manual change to a selection field.

Accepting an offer copies its buyer and price onto the property and changes the property to Offer Accepted. The server rejects a second accepted offer and incompatible terminal transitions. The checks live in Python so they also apply when an action is called outside the visible form.

**Try it:** Add two offers, accept one, and inspect the property's buyer, selling price, and state. Try accepting the other offer or cancelling a sold property and read the resulting error.

## Chapter 10 - Constraints

[Official chapter](https://www.odoo.com/documentation/20.0/developer/tutorials/server_framework_101/10_constraints.html)

The workflow now needs data rules that apply no matter how a record is created. PostgreSQL constraints require positive expected and offer prices, allow a zero but not negative selling price, and prevent duplicate type or tag names. Odoo 20 declares these rules with `models.Constraint`.

A Python constraint handles the more involved rule: once a selling price is nonzero, it must be at least 90% of the expected price. It checks both price fields and uses Odoo's float comparison helpers. Keeping this rule on the model protects records created through imports and RPC calls as well as forms.

**Try it:** Enter a negative expected price, a zero offer, and a selling price below 90% of the expected price. Compare the errors with a duplicate property type name.

## Chapter 11 - Add the sprinkles

[Official chapter](https://www.odoo.com/documentation/20.0/developer/tutorials/server_framework_101/11_sprinkles.html)

This chapter makes the existing workflow easier to scan and use. Property states appear in a status bar; colored tags and row decorations highlight important records. Offer and tag lists can be edited inline, the availability column can be shown when needed, and the Available filter is selected by default. Searching living area now means “at least this much area.”

Ordering also becomes deliberate: newer properties come first, higher offers come first, tags sort by name, and property types can be reordered with a drag handle. A property type form shows its properties and an Offers count. The count opens an action filtered to offers for that type through a stored related field.

Buttons, garden details, and offer editing are shown only when relevant. These view rules guide data entry; Python actions and constraints remain responsible for enforcing the business rules.

**Try it:** Reorder property types, assign a tag color, search for a minimum living area, and open a type's Offers count. Compare what the UI hides with what the server still validates.

## Chapter 12 - Inheritance

[Official chapter](https://www.odoo.com/documentation/20.0/developer/tutorials/server_framework_101/12_inheritance.html)

Inheritance lets an addon add behavior without replacing Odoo's existing models. An `@api.ondelete` method now prevents deletion of a property once it enters an active or completed workflow; New and Cancelled properties remain deletable. Offer creation also checks the current highest price and changes the property to Offer Received.

The addon extends `res.users` with a relation to properties assigned to that salesperson. An inherited user form adds a Properties tab after Preferences and shows only New or Offer Received properties. The original user model and form still belong to Odoo; our addon contributes only the extension.

**Try it:** Create an offer, try a lower one, and try deleting the property. Then open the salesperson's user form and compare its Properties tab with the property's `user_id`.

## Chapter 13 - Interact with other modules

[Official chapter](https://www.odoo.com/documentation/20.0/developer/tutorials/server_framework_101/13_other_module.html)

Real estate management can be useful without Invoicing. The separate `estate_account` addon depends on both `estate` and `account`, so invoice creation is available only when the integration addon is installed. This keeps the base estate addon independent of accounting.

`estate_account` extends the property's Sold action through `super()`. After an accepted buyer is available, it creates a draft customer invoice with two lines: 6% of the selling price for commission and 100 for administrative fees. `Command.create` adds both lines as part of the invoice creation.

**Try it:** Install `estate_account`, accept an offer, mark the property Sold, and find the draft invoice. Check both line amounts and compare the installed dependencies of `estate` and `estate_account`.

## Chapter 14 - A brief history of QWeb

[Official chapter](https://www.odoo.com/documentation/20.0/developer/tutorials/server_framework_101/14_qwebintro.html)

A kanban view uses a QWeb `card` template to render each property. The new view shows the property name, expected price, and tags. It shows the best offer when the state is Offer Received and the selling price after an offer has been accepted. The `state` field is loaded for those `t-if` conditions even though it is not displayed as its own line.

Cards are grouped by property type by default. Dragging records is disabled so moving a card cannot silently change its type. The property action now offers both list and kanban views over the same records.

**Try it:** Switch to kanban and compare cards in New, Offer Received, Offer Accepted, and Sold states. Change a property's type and observe which group contains its card.

## Chapter 15 - The final word

[Official chapter](https://www.odoo.com/documentation/20.0/developer/tutorials/server_framework_101/15_final_word.html)

The finished application connects the ideas from the earlier chapters: models hold property data, access rules decide who can use it, views present it, actions move it through a workflow, and constraints keep it valid. Inheritance extends Odoo's users, while `estate_account` adds optional invoicing without changing the base estate dependency list.

This chapter makes no addon code changes. The code review and lint corrections were kept with the commits that introduced the relevant files, so each chapter remains a coherent checkpoint. The complete workflow runs from a property and accepted offer to a draft customer invoice.

**Try it:** Follow that workflow from start to finish. Then explore the [Odoo Runbot](https://runbot.odoo.com/) and look for another app using the same model, view, action, and status-bar ideas.
