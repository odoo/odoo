import { Component, proxy, t, useProps } from "@odoo/owl";

export class QWebPicker extends Component {
    static template = "html_editor.QWebPicker";
    props = useProps({
        groups: t.any(),
        select: t.any(),
        expression: t.any().optional(),
    });

    setup() {
        this.state = proxy({ groups: this.props.groups });
    }

    onChange(ev) {
        const [groupIndex, elementIndex] = ev.target.value.split(",");
        this.props.select(this.state.groups[groupIndex][elementIndex].node);
    }
}
