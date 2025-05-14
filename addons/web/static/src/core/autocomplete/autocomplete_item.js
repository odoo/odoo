import { Component } from "@odoo/owl";

export class AutoCompleteItem extends Component {
    static components = {};
    static template = "web.AutoComplete.Item";
    static props = {
        id: { type: String, optional: true },
        class: { type: String, optional: true },
        unselectable: { type: Boolean, optional: true },
        attrs: {
            type: Object,
            optional: true,
        },
        onSelected: {
            type: Function,
            optional: true,
        },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        class: "",
        unselectable: false,
    };
}
