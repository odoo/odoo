/** @odoo-module */

import { registry } from "@web/core/registry";
const fieldRegistry = registry.category("fields");

export function getFieldClassFromRegistry(viewType, fieldType, widget) {
    if (viewType && widget) {
        const name = `${viewType}.${widget}`;
        if (fieldRegistry.contains(name)) {
            return fieldRegistry.get(name);
        }
    }

    if (widget) {
        if (fieldRegistry.contains(widget)) {
            return fieldRegistry.get(widget);
        }
    }

    if (viewType && fieldType) {
        const name = `${viewType}.${fieldType}`;
        if (fieldRegistry.contains(name)) {
            return fieldRegistry.get(name);
        }
    }

    if (fieldRegistry.contains(fieldType)) {
        return fieldRegistry.get(fieldType);
    }

    return null;
}
