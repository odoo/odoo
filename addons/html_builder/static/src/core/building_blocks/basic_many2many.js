import { Component } from "@odoo/owl";
import { basicContainerBuilderComponentProps } from "../utils";
import { SelectMany2X } from "./select_many2x";

export class BasicMany2Many extends Component {
    static template = "html_builder.BasicMany2Many";
    static props = {
        ...basicContainerBuilderComponentProps,
        model: String,
        fields: { type: Array, element: String, optional: true },
        domain: { type: Array, optional: true },
        limit: { type: Number, optional: true },
        selection: { type: Array, element: Object },
        setSelection: Function,
        create: { type: Function, optional: true },
    };
    static components = { SelectMany2X };

    select(entry) {
        this.props.setSelection([...this.props.selection, entry]);
    }
    unselect(id) {
        this.props.setSelection([...this.props.selection.filter((item) => item.id !== id)]);
    }
}
