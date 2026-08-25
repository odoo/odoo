import { Component, proxy, signal, t, useProps } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import {
    useDropdownAutoVisibility,
    useToolbarDropdownPreview,
    useToolbarDropdownFocus,
} from "@html_editor/toolbar_dropdown_hook";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

export class AlignSelector extends Component {
    static template = "html_editor.AlignSelector";
    props = useProps({
        getItems: t.function(),
        getDisplay: t.function(),
        focusEditable: t.function(),
        previewable: t.function(),
        ...toolbarButtonProps,
    });
    static components = { Dropdown, DropdownItem };

    alignSelector = signal.ref();

    setup() {
        this.items = this.props.getItems();
        this.state = proxy(this.props.getDisplay());
        this.menuRef = signal.ref();
        this.dropdown = useDropdownState();
        useToolbarDropdownFocus(this.dropdown, this.alignSelector);
        useDropdownAutoVisibility(this.env.overlayState, this.menuRef);
        this.preview = useToolbarDropdownPreview({
            dropdown: this.dropdown,
            previewable: this.props.previewable,
        });
    }

    onSelected(item) {
        this.preview.commit(item);
        this.props.focusEditable();
    }
}
