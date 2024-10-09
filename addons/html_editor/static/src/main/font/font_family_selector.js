import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class FontFamilySelector extends Component {
    static template = "html_editor.FontFamilySelector";
    static props = {
        document: { optional: true },
        fontFamilyItems: Object,
        currentFontFamily: Object,
        onSelected: Function,
        ...toolbarButtonProps,
    };
    static components = { Dropdown, DropdownItem };
}
