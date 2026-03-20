import { Component, useState } from "@odoo/owl";

export class QWebPicker extends Component {
    static template = "html_editor.QWebPicker";
    static props = ["groups", "select"];

    setup() {
        this.state = useState({ groups: this.props.groups });
    }

    onChange(ev) {
        const [groupIndex, elementIndex] = ev.target.value.split(",");
        this.props.select(this.state.groups[groupIndex][elementIndex].node);
    }
}
