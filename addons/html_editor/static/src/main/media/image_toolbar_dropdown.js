import { Component, proxy, signal } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import {
    useDropdownAutoVisibility,
    useToolbarDropdownFocus,
    useToolbarDropdownPreview,
} from "@html_editor/toolbar_dropdown_hook";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

export class ImageToolbarDropdown extends Component {
    static components = { Dropdown, DropdownItem };
    static props = {
        ...toolbarButtonProps,
        name: String,
        icon: { type: String, optional: true },
        focusEditable: Function,
        previewable: Function,
        items: Array,
        getDisplay: { type: Function, optional: true },
    };
    static template = "html_editor.ImageToolbarDropdown";

    imageToolbarBtn = signal.ref();

    setup() {
        this.items = this.props.items;
        if (this.props.getDisplay) {
            this.state = proxy(this.props.getDisplay());
        }
        this.menuRef = signal.ref();
        this.dropdown = useDropdownState();
        useToolbarDropdownFocus(this.dropdown, this.imageToolbarBtn);
        useDropdownAutoVisibility(this.env.overlayState, this.menuRef);
        this.preview = useToolbarDropdownPreview({
            dropdown: this.dropdown,
            getItems: () => this.items,
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
