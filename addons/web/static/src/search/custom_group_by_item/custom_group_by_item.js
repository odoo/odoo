// @ts-check

/** @module @web/search/custom_group_by_item/custom_group_by_item - Dropdown item for selecting a custom field to group by */

import { Component } from "@odoo/owl";

/** Dropdown item that lets the user pick a field to group by. */
export class CustomGroupByItem extends Component {
    static template = "web.CustomGroupByItem";
    static props = {
        fields: Array,
        onAddCustomGroup: Function,
    };

    /** @returns {Array<{label: string, value: string}>} */
    get choices() {
        return this.props.fields.map((f) => ({
            label: f.string,
            value: f.name,
        }));
    }

    /** @param {Event} ev */
    onSelected(ev) {
        if (ev.target.value) {
            this.props.onAddCustomGroup(ev.target.value);
            // reset the placeholder
            ev.target.value = "";
        }
    }
}
