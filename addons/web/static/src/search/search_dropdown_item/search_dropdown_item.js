/** @odoo-module **/

import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class SearchDropdownItem extends DropdownItem {}
SearchDropdownItem.template = "web.SearchDropdownItem";
SearchDropdownItem.props = {
    ...DropdownItem.props,
    checked: {
        type: Boolean,
        optional: false,
    },
};
