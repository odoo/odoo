import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import {
    useDropdownAutoVisibility,
    useToolbarDropdownFocus,
} from "@html_editor/toolbar_dropdown_hook";
import { useChildRef } from "@web/core/utils/hooks";
import { useRef } from "@web/owl2/utils";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

export class FontFamilySelector extends Component {
    static template = "html_editor.FontFamilySelector";
    static props = {
        document: { optional: true },
        fontFamilyItems: Object,
        currentFontFamily: Object,
        onSelected: Function,
        focusEditable: Function,
        ...toolbarButtonProps,
    };
    static components = { Dropdown, DropdownItem };

    setup() {
        this.menuRef = useChildRef();
        this.fontFamilySelector = useRef("fontFamilySelector");
        this.dropdown = useDropdownState();
        useToolbarDropdownFocus(this.dropdown, this.fontFamilySelector);
        useDropdownAutoVisibility(this.env.overlayState, this.menuRef);
    }

    onSelected(item) {
        this.props.onSelected(item);
        this.props.focusEditable();
    }
}
