# Product External ID Display

This module adds a visible External ID field to product forms and views in Odoo.

## Purpose

When importing/exporting data between Odoo and external systems, it's often necessary to reference the External ID (also known as XML ID) of products. However, by default, Odoo doesn't show the External ID in the interface, making it difficult to know which identifier to use when creating data that references products.

This module solves that problem by displaying the External ID as a read-only field on product forms and list views.

## Features

- Shows the External ID as a read-only field on product template forms
- Shows the External ID as a read-only field on product variant forms
- Adds External ID to product list views (optional column)
- Makes External ID searchable in product search views

## Installation

1. Place the `product_external_id` module in your Odoo addons directory
2. Update the addons list: Settings -> Technical -> Modules -> Update Apps List
3. Install the module: Apps -> search for "Product External ID Display" -> Install

## Usage

Once installed, the External ID will be visible:

1. In product forms, next to the Internal Reference field
2. In product list views as an optional column
3. In product search, allowing you to search by External ID

## Benefits

- Simplifies working with Bills of Materials (BoMs) when integrating with external systems
- Makes it easier to identify which products are being referenced in imported/exported data
- Eliminates the need to export products just to obtain their External IDs

## Technical Notes

- The module uses a computed field to retrieve the External ID from the `ir.model.data` table
- For products with multiple External IDs, only the first one found is displayed
- The field is read-only as External IDs should be managed via data import/export or developer tools 