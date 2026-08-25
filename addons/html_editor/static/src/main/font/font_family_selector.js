import { Component, signal } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import {
    useDropdownAutoVisibility,
    useToolbarDropdownPreview,
    useToolbarDropdownFocus,
} from "@html_editor/toolbar_dropdown_hook";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

export class FontFamilySelector extends Component {
    static template = "html_editor.FontFamilySelector";
    static props = {
        document: { optional: true },
        fontFamilyItems: Object,
        currentFontFamily: Object,
        focusEditable: Function,
        previewable: Function,
        ...toolbarButtonProps,
    };
    static components = { Dropdown, DropdownItem };

    fontFamilySelector = signal.ref();

    setup() {
        this.menuRef = signal.ref();
        this.dropdown = useDropdownState();
        useToolbarDropdownFocus(this.dropdown, this.fontFamilySelector);
        useDropdownAutoVisibility(this.env.overlayState, this.menuRef);
        this.preview = useToolbarDropdownPreview({
            dropdown: this.dropdown,
            getItems: () => this.props.fontFamilyItems,
            previewable: this.props.previewable,
        });
    }

    onSelected(item) {
        this.preview.commit(item);
        this.props.focusEditable();
    }

    onItemHoverOut() {
        this.preview.reset();
    }
}
