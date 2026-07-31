# My Custom Table Module (my_custom_table_module)

**Version:** 1.0

## Summary

This is a very basic Odoo module created for demonstration purposes. Its sole function is to define a simple data model (`my.simple.data`), which causes Odoo to automatically create a corresponding table (`my_simple_data`) in the PostgreSQL database when the module is installed.

## Purpose

This module serves as a minimal example of how to:
* Structure a basic Odoo addon module.
* Define a new model using `odoo.models.Model`.
* Leverage Odoo's ORM to automatically create database tables based on model definitions.

## Dependencies

* `base` (Odoo's base module)

## Installation

1.  **Place the Module:** Copy or clone the `my_custom_table_module` directory into a directory included in your Odoo server's `addons_path`. It is recommended to use a separate custom addons directory rather than placing it inside the standard Odoo `addons` folder.
    *Example:* If you created `~/odoo-custom-addons`, place it there: `~/odoo-custom-addons/my_custom_table_module/`
    *Ensure your Odoo configuration file (`odoo.conf`) includes the path to your custom addons directory in the `addons_path` setting.*
2.  **Restart Odoo Server:** Restart the Odoo server process for it to detect the new module. In pycharm simply rerun the config
3.  **Update Apps List:**
    * Log into your Odoo database as an administrator.
    * Activate Developer Mode (Settings -> General Settings -> Activate the developer mode).
    * Go to the `Apps` menu.
    * Click `Update Apps List` and confirm.
4.  **Install Module:**
    * Remove the `Apps` filter from the search bar.
    * Search for `My Custom Table Module`.
    * Click the `Install` button.

## Verification

After successful installation, the table `my_simple_data` should exist in your Odoo database. You can verify this using a PostgreSQL client like `psql`:

1.  Connect to your database: `psql -d your_database_name`
2.  Run the describe command: `\d my_simple_data;`
3.  You should see the table definition including columns like `id`, `name`, `description`, `record_date`, `is_active`, `create_uid`, `create_date`, `write_uid`, and `write_date`.

## Usage

This module does not provide any user interface elements (views or menus) by default. It only creates the backend table structure. Further development would be needed to create views to interact with the data in this table via the Odoo UI.

## Author

Your Name

## License

LGPL-3
