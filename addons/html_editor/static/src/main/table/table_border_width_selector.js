import { Component, proxy, signal, t, useProps } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import {
    useDropdownAutoVisibility,
    useToolbarDropdownPreview,
} from "@html_editor/toolbar_dropdown_hook";

export class TableBorderWidthSelector extends Component {
    static template = "html_editor.TableBorderWidthSelector";
    props = useProps({
        getItems: t.function(),
        getDisplay: t.function(),
        previewable: t.function(),
        ...toolbarButtonProps,
    });
    static components = { Dropdown, DropdownItem };

    setup() {
        this.items = this.props.getItems();
        this.state = proxy(this.props.getDisplay());
        this.menuRef = signal.ref();
        this.dropdown = useDropdownState();
        useDropdownAutoVisibility(this.env.overlayState, this.menuRef);
        this.preview = useToolbarDropdownPreview({
            dropdown: this.dropdown,
            previewable: this.props.previewable,
        });
    }

    onSelected(item) {
        this.preview.commit(item);
    }
}
