import { Component, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";

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
    }

    onSelected(item) {
        this.props.onSelected(item);
    }
}
