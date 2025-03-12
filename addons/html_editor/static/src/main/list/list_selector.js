import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { toolbarButtonProps } from "../toolbar/toolbar";
import { closestElement } from "@html_editor/utils/dom_traversal";

export class ListSelector extends Component {
    static template = "html_editor.ListSelector";
    static props = {
        ...toolbarButtonProps,
        getButtons: Function,
        getListMode: Function,
        key: Object,
    };
    static components = { Dropdown };

    getActiveMode() {
        const { editableSelection: selection } = this.props.getSelection();
        const closestLI = closestElement(selection.anchorNode, "LI");
        return closestLI && this.props.getListMode(closestLI.parentNode);
    }
}
