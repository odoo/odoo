/** @odoo-module */

import { Component, useState } from "@odoo/owl";

export class ObjectRenderer extends Component {
    static template = "pos_owlybook.ObjectRenderer";

    setup() {
        this.uncollapsed = useState({});
    }

    isObject(value) {
        return typeof value === "object";
    }

    isArray(value) {
        return Array.isArray(value);
    }

    openingBracket(object) {
        return this.isArray(object) ? "[" : "{";
    }

    closingBracket(object) {
        return this.isArray(object) ? "]" : "}";
    }

    toggleCollapse(uncollapsedObject, name) {
        if (uncollapsedObject[name]) {
            uncollapsedObject[name] = undefined;
        } else {
            uncollapsedObject[name] = {};
        }
    }
}
