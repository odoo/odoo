// @ts-check

/** @module @web/components/dropdown/checkbox_item - Dropdown menu item variant with an integrated checkbox toggle */

import { DropdownItem } from "@web/components/dropdown/dropdown_item";

export class CheckboxItem extends DropdownItem {
    static template = "web.CheckboxItem";
    static props = {
        ...DropdownItem.props,
        checked: {
            type: Boolean,
            optional: false,
        },
    };
}
