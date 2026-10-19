import { Component, useExternalListener, useRef } from "@odoo/owl";

export class CustomGroupByItem extends Component {
    static template = "web.CustomGroupByItem";
    static props = {
        fields: Array,
        onAddCustomGroup: Function,
    };

    setup() {
        this.selectRef = useRef("selectElement");
        useExternalListener(window, "click", (ev) => {
            const select = this.selectRef.el;
            if (select && !select.contains(ev.target)) {
                select.value = "";
            }
        });
    }

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
