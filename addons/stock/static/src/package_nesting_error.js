import { registry } from "@web/core/registry";

// Attempting to nest packages of the same type violates a constraint and yields
// a validation error that must be displayed as a notification rather than an
// error popup across the backend and the frontend alike.

registry.category("error_notifications").add(
    "odoo.addons.stock.models.stock_package.PackageTypeNestingError",
    { type: "danger" },
);
