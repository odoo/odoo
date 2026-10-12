import { Component, t, useProps } from "@odoo/owl";

export class CustomGroupByItem extends Component {
    static template = "web.CustomGroupByItem";
    props = useProps({
        fields: t.array(),
        onAddCustomGroup: t.function(),
    });

    get choices() {
        return this.props.fields.map((f) => ({ label: f.string, value: f.name }));
    }

    onSelected(ev) {
        if (ev.target.value) {
            this.props.onAddCustomGroup(ev.target.value);
            // reset the placeholder
            ev.target.value = "";
        }
    }
}
