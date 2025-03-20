import { Component, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import { useDropdownAutoVisibility } from "@html_editor/dropdown_autovisibility_hook";
import { useChildRef } from "@web/core/utils/hooks";

export class TableAlignSelector extends Component {
    static template = "html_editor.TableAlignSelector";
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
