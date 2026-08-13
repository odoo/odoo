import { DropdownItem } from "@web/core/dropdown/dropdown_item";

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
