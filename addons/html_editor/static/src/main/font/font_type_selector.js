import { Component, proxy, signal, t, useProps } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { PreviewableDropdownItem } from "@html_editor/main/toolbar/previewable_dropdown_item";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import {
    useDropdownAutoVisibility,
    useToolbarDropdownPreview,
    useToolbarDropdownFocus,
} from "@html_editor/toolbar_dropdown_hook";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

export class FontTypeSelector extends Component {
    static template = "html_editor.FontTypeSelector";
    props = useProps({
        ...toolbarButtonProps,
        getItems: t.function(),
        getDisplay: t.function(),
        previewableOperation: t.object(),
    });
    static components = { Dropdown, PreviewableDropdownItem };

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
            menuRef: this.menuRef,
            previewableOperation: this.props.previewableOperation,
        });
    }

    onSelected(item) {
        this.preview.commit(item);
    }
}
