/** @odoo-module **/

import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class CheckboxItem extends DropdownItem {}
CheckboxItem.template = "web.CheckboxItem";
CheckboxItem.props = {
    ...DropdownItem.props,
    checked: {
        type: Boolean,
        optional: false,
    },
};
