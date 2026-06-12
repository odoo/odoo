import { props, t } from "@odoo/owl";
import { DropdownItem, dropdownItemProps } from "@web/core/dropdown/dropdown_item";

export class CheckboxItem extends DropdownItem {
    static template = "web.CheckboxItem";
    props = props({
        ...dropdownItemProps,
        checked: t.boolean(),
    });
}
