# Odoo Module: Simple Library (`library_simple`)

**Version:** 18.0.1.0
**Author:** [prithvi]
**License:** LGPL-3

## Purpose

This module serves as a minimal, practical example demonstrating core Odoo framework concepts for building modular applications. It implements a very basic library book management system.

## Features

* **Book Model (`library.book`):** Defines a new model to store book information (Title, Synopsis, Active status).
* **Basic Business Logic:** Includes a constraint to ensure book titles are not empty and overrides the `copy()` method.
* **Views:** Provides Tree (List) and Form views for managing books.
* **Menu Item:** Adds a "Library" top-level menu with a "Books" submenu to access the book views.
* **Security:** Implements basic access control using `ir.model.access.csv`, granting standard internal users full CRUD permissions on books.
* **Model Extension:** Demonstrates inheriting an existing Odoo model (`res.partner`) to add a new field (`favorite_book_id` - a Many2one relationship to `library.book`).
* **View Extension:** Inherits the standard Partner form view to display the new `favorite_book_id` field on a dedicated tab.
* **JSON Controller:** Includes a simple HTTP controller (`/library/books`) that returns a list of active books in JSON format (requires authenticated user).

## Installation

1.  **Ensure Dependencies:** Make sure the required Odoo modules (`base`, `web`) are installed in your database.
2.  **Add to Addons Path:** Place the `library_simple` directory into a folder included in your Odoo instance's `addons_path` configuration (e.g., a `custom-addons` directory).
    * Example `odoo.conf` entry: `addons_path = /path/to/odoo/addons, /path/to/custom-addons`
3.  **Restart Odoo Server:** Restart the Odoo server process so it recognizes the new module.
    ```bash
    # Example (if running manually)
    ./odoo-bin -c odoo.conf
    # Or using system service
    sudo systemctl restart odoo
    ```
4.  **Update Apps List:**
    * Log in to your Odoo instance with an administrator account.
    * Activate Developer Mode (Settings -> Activate the developer mode).
    * Navigate to the `Apps` menu.
    * Click `Update Apps List` in the menu.
5.  **Install Module:**
    * Search for `Simple Library` or `library_simple` in the Apps menu (you might need to remove the default "Apps" filter).
    * Click the `Install` button on the `library_simple` module card.

## Configuration

No specific configuration is required for this module after installation.

## Usage

* **Managing Books:** Navigate to the `Library` menu in the main Odoo interface, then click the `Books` submenu. You can create, view, edit, and archive book records using the standard Odoo interface.
* **Favorite Book on Contacts:** Go to the `Contacts` app, open or create a contact record. You will find a new tab named "Library Info" where you can select a "Favorite Book" from the available books.
* **JSON Endpoint:** Authenticated users can access the list of active books programmatically by sending a GET request to `/library/books` on your Odoo instance's URL (e.g., `http://<your_odoo_domain>:8069/library/books`). This requires appropriate authentication (e.g., session cookie or API key).

## Technical Concepts Illustrated

This module demonstrates:

* Defining new models (`odoo.models.Model`).
* Using various field types (`fields.Char`, `fields.Text`, `fields.Boolean`, `fields.Many2one`).
* Implementing model constraints (`@api.constrains`).
* Overriding standard model methods (`copy`).
* Defining basic security rules (`ir.model.access.csv`).
* Creating views (Tree, Form) using XML (`ir.ui.view`).
* Creating menu items and window actions (`ir.ui.menu`, `ir.actions.act_window`).
* Extending existing models using `_inherit`.
* Extending existing views using XML inheritance (`<xpath>`).
* Creating simple JSON web controllers (`odoo.http.Controller`, `@http.route`).
* Using the ORM environment within controllers (`request.env`).

## Dependencies

* `base`
* `web`

---

python ./odoo-bin -c odoo.conf --log-level=info