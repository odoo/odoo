# Real Estate: Server Framework 101

`estate` is a training addon that follows the
[Server framework 101](https://www.odoo.com/documentation/20.0/developer/tutorials/server_framework_101.html)
tutorial. It manages real estate advertisements: properties put on sale, the offers buyers make on
them, and the sale itself.

The addon is built **one commit per chapter**. To learn from it, read a chapter of the official
tutorial, then inspect the matching commit:

```sh
git log --oneline --reverse -- addons/estate addons/estate_account
git show <commit>
```

Each chapter below explains:

- **Functional**: what changes for the user of the application.
- **Technical**: which framework concepts the commit uses, and why.
- **Try it**: a small manual check to do in the browser before moving on.

The code targets the current master branch (`saas~20.1`). Where the framework changed since the
tutorial was written, the chapter says so.

## Chapter 1 - Architecture overview

[Official chapter](https://www.odoo.com/documentation/20.0/developer/tutorials/server_framework_101/01_architecture.html)

**Functional.** Nothing to use yet: this chapter only explains where each piece of the application
will live.

**Technical.** Odoo is a three-tier application:

| Tier | Technology | In this addon |
| --- | --- | --- |
| Presentation | Owl web client (HTML, JS, CSS) | XML views rendered by the web client |
| Logic | Python server | `models/*.py`: fields, computes, constraints, actions |
| Data | PostgreSQL | one table per model, created and updated by the ORM |

An *addon* (also called a *module*) groups everything that belongs to one feature:

```
estate/
|-- __init__.py          # imports the Python packages of the addon
|-- __manifest__.py      # name, dependencies and data files loaded at install/upgrade
|-- models/              # business objects (Python classes mapped to tables)
|-- views/               # how records are shown: actions, menus, list/form/search views
|-- security/            # who may read, create, write or delete each model
`-- static/description/  # icon shown in the Apps list and the main menu
```

An addon is installed **per database**: the code is on disk once, but each database decides whether
it uses it. Installing or upgrading the addon is what creates the tables and loads the XML/CSV data.

**Try it.** Open an existing addon such as `addons/fleet`. Find its manifest, one model file and one
view file, and decide which of them stores a vehicle's license plate and which one displays it.

## Chapter 2 - A new application

[Official chapter](https://www.odoo.com/documentation/20.0/developer/tutorials/server_framework_101/02_newapp.html)

**Functional.** "Real Estate" appears in the Apps menu with its own icon and can be installed. It
does nothing yet: there is no model and no menu.

**Technical.**

- Odoo discovers an addon by scanning the folders of the `--addons-path` for a `__manifest__.py`.
- `__init__.py` makes the folder a Python package. It is empty for now; later chapters import the
  `models` package from it.
- The manifest is a Python dictionary:
  - `depends` lists the addons that must be installed first. Every addon depends at least on
    `base`, which provides users, companies, partners and the ORM models themselves.
  - `application=True` marks the addon as an app (a top-level product) instead of a technical
    module; only apps show up with the default filter of the Apps menu.
  - `category` groups the addon in the Apps menu and, later, in the user access settings.
- `static/description/icon.png` (100x100 px) is picked up automatically as the icon in the Apps
  menu. Chapter 5 reuses it as the icon of the main menu.

**Try it.** Start the server with `-u estate` or update the Apps list in debug mode, then remove the
"Apps" filter and search for "Real Estate". Install it: the installation succeeds although nothing
new appears in the main menu.

## Chapter 3 - Models and basic fields

[Official chapter](https://www.odoo.com/documentation/20.0/developer/tutorials/server_framework_101/03_basicmodel.html)

**Functional.** The application can now store properties: a title, a description, a postcode, the
availability date, the expected and selling prices, and details such as bedrooms, areas, garage and
garden. There is still no screen to see them (chapter 5).

**Technical.**

- A model is a Python class inheriting `models.Model`. `_name` is its technical name and
  `_description` its human-readable name. When the addon is installed or upgraded, the ORM creates
  or alters the `estate_property` table so that its columns match the fields.
- Simple fields map to one column each: `Char` (short text), `Text` (long text), `Integer`,
  `Float`, `Boolean`, `Date` and `Selection` (a fixed list of `(key, label)` pairs).
- `required=True` adds a `NOT NULL` constraint in the database and makes the field mandatory in the
  forms. `name` and `expected_price` are required because a property without them makes no sense.
- `string` is the label shown in the interface. Without it, Odoo derives one from the field name.
- The ORM adds automatic fields to every model: `id`, `create_date`, `create_uid`, `write_date`,
  `write_uid` and `display_name` (computed from `name` by default).
- `estate/__init__.py` imports `models`, and `models/__init__.py` imports each model file: a file
  that is not imported is never loaded.

**Try it.** Upgrade the addon and look at the table in `psql`:

```sh
psql <db> -c '\d estate_property'
```

Compare the columns with the fields, and find the automatic columns. The server log also warns
`The model estate.property has no access rules`: chapter 4 fixes that.

## Chapter 4 - Security: a brief introduction

[Official chapter](https://www.odoo.com/documentation/20.0/developer/tutorials/server_framework_101/04_securityintro.html)

**Functional.** Every internal user (employee) may create, read, update and delete properties.
Portal and public users have no access at all.

**Technical.**

- A new model is closed by default: without an access row nobody but the superuser can use it,
  and the server logs a warning.
- Access rows are ordinary data records loaded from `security/ir.access.csv`, listed in the
  manifest's `data` key. The CSV file name is the model the rows are loaded into (`ir.access`);
  the columns are its fields:

  | Column | Meaning |
  | --- | --- |
  | `id` | XML id of the row, so that upgrades update it instead of creating a duplicate |
  | `name` | free label |
  | `model_id` | the model the row grants access to |
  | `group_id/id` | the group whose members get the access (`base.group_user` = internal users); empty = everyone |
  | `operation` | the granted operations, a subset of `crud` (create, read, update, delete) |
  | `domain` | optional: limits the access to the records matching this domain (empty = all) |

- **Framework change.** The tutorial still shows `ir.model.access.csv`, with one boolean column per
  operation (`perm_read`, `perm_write`, ...), plus separate record rules (`ir.rule`) for
  per-record restrictions. On master, both are merged into `ir.access`: `operation` replaces the
  four booleans and `domain` replaces the record rule.
- The security file comes first in `data` because later files (menus) refer to models and groups,
  and a data file can only reference what was loaded before it.

**Try it.** Upgrade the addon: the "no access rules" warning is gone. In Settings > Technical >
Security > Access, search for "estate" to find the loaded row.

## Chapter 5 - Finally, some UI to play with

[Official chapter](https://www.odoo.com/documentation/20.0/developer/tutorials/server_framework_101/05_firstui.html)

**Functional.**

- The main menu shows the "Real Estate" app with its icon. Real Estate > Advertisements >
  Properties lists the properties and lets the user create them.
- A new property is available three months from today and has two bedrooms by default.
- The selling price cannot be typed: it will come from the accepted offer (chapter 9).
- Duplicating a property does not copy its availability date, its selling price or its status.
- Properties can be archived instead of deleted, and every property has a status, starting at
  "New".

**Technical.**

- **Window action** (`ir.actions.act_window`): opens a model in the given `view_mode`s. Its
  `help` is the message shown when the list is empty.
- **Menus** (`<menuitem>`): nested menu items build the hierarchy; only a leaf has an `action`.
  `web_icon` on the root menu reuses the app icon of chapter 2. Menus refer to the action by XML
  id, so `estate_menus.xml` is loaded after `estate_property_views.xml`.
- Odoo generates a basic list and form view when none is defined: they are replaced in chapter 6.
- **Field attributes**:
  - `default`: a value, or a callable evaluated at creation time. The lambda calls
    `fields.Date.context_today(self)` so that "today" is computed in the user's time zone.
  - `readonly=True`: the field cannot be edited in the interface (code can still write it).
  - `copy=False`: the value is not copied by `copy()`, i.e. the "Duplicate" action.
- **Reserved fields**: `active` gives archiving for free (archived records are hidden unless
  searched explicitly), and `state` is the conventional name for a record's workflow status.

**Try it.** Create a property and check its defaults. Duplicate it and compare the availability
dates and statuses. Archive one (Actions > Archive) and notice it disappears from the list.
