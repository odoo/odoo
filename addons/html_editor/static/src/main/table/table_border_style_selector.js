import { Component, proxy, signal, t, useProps } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import { useDropdownAutoVisibility } from "@html_editor/toolbar_dropdown_hook";

export class TableBorderStyleSelector extends Component {
    static template = "html_editor.TableBorderStyleSelector";
    static components = { Dropdown, DropdownItem };

    props = useProps({
        ...toolbarButtonProps,
        getItems: t.function(),
        getDisplay: t.function(),
        onSelected: t.function(),
    });

    setup() {
        this.items = this.props.getItems();
        this.state = proxy(this.props.getDisplay());
        this.menuRef = signal.ref();
        useDropdownAutoVisibility(this.env.overlayState, this.menuRef);
    }

    onSelected(item) {
        this.props.onSelected(item);
    }
}
