import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { toolbarButtonProps } from "../toolbar/toolbar";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { useDropdownAutoVisibility } from "@html_editor/dropdown_autovisibility_hook";
import { useChildRef } from "@web/core/utils/hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class ListSelector extends Component {
    static template = "html_editor.ListSelector";
    static props = {
        ...toolbarButtonProps,
        getButtons: Function,
        getListMode: Function,
        key: Object,
    };
    static components = { Dropdown, DropdownItem };

    setup() {
        this.menuRef = useChildRef();
        useDropdownAutoVisibility(this.env.overlayState, this.menuRef);
    }
    getActiveMode() {
        const { editableSelection: selection } = this.props.getSelection();
        const closestLI = closestElement(selection.anchorNode, "LI");
        return closestLI && this.props.getListMode(closestLI.parentNode);
    }

    onSelected(ev, button) {
        button.run();
        // Keep focus on the item so Escape returns to the dropdown button
        ev.target.focus();
    }
}
