import { Component, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import { useChildRef } from "@web/core/utils/hooks";
import { useDropdownAutoVisibility } from "@html_editor/dropdown_autovisibility_hook";

export class ImageToolbarDropdown extends Component {
    static components = { Dropdown, DropdownItem };
    static props = {
        ...toolbarButtonProps,
        name: String,
        icon: { type: String, optional: true },
        onSelected: Function,
        items: Array,
        getDisplay: { type: Function, optional: true },
    };
    static template = "html_editor.ImageToolbarDropdown";

    setup() {
        this.items = this.props.items;
        if (this.props.getDisplay) {
            this.state = useState(this.props.getDisplay());
        }
        this.menuRef = useChildRef();
        useDropdownAutoVisibility(this.env.overlayState, this.menuRef);
    }

    onSelected(item) {
        this.props.onSelected(item);
    }
}
