/** @odoo-module native */
import { useDropdownAutoVisibility } from "@html_editor/dropdown_autovisibility_hook";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import { Component, useState } from "@odoo/owl";
import { Dropdown } from "@web/components/dropdown";
import { useChildRef } from "@web/core/utils/hooks";

export class TableBorderWidthSelector extends Component {
    static template = "html_editor.TableBorderWidthSelector";
    static props = {
        getItems: Function,
        getDisplay: Function,
        onSelected: Function,
        ...toolbarButtonProps,
    };
    static components = { Dropdown };

    setup() {
        this.items = this.props.getItems();
        this.state = useState(this.props.getDisplay());
        this.menuRef = useChildRef();
        useDropdownAutoVisibility(this.env.overlayState, this.menuRef);
    }

    onSelected(item) {
        this.props.onSelected(item);
    }
}
