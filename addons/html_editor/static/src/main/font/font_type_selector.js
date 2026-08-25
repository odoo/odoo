import { Component, proxy, signal } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import {
    useDropdownAutoVisibility,
    useToolbarDropdownPreview,
    useToolbarDropdownFocus,
} from "@html_editor/toolbar_dropdown_hook";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

export class FontTypeSelector extends Component {
    static template = "html_editor.FontTypeSelector";
    static props = {
        ...toolbarButtonProps,
        getItems: Function,
        getDisplay: Function,
        previewable: Function,
    };
    static components = { Dropdown, DropdownItem };

    fontTypeSelector = signal.ref();

    setup() {
        this.items = this.props.getItems();
        this.state = proxy(this.props.getDisplay());
        this.menuRef = signal.ref();
        this.dropdown = useDropdownState();
        useDropdownAutoVisibility(this.env.overlayState, this.menuRef);
        useToolbarDropdownFocus(this.dropdown, this.fontTypeSelector);
        this.preview = useToolbarDropdownPreview({
            dropdown: this.dropdown,
            getItems: () => this.items,
            previewable: this.props.previewable,
        });
    }

    onSelected(item) {
        this.preview.commit(item);
    }

    onItemHoverOut() {
        this.preview.reset();
    }
}
