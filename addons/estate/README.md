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
