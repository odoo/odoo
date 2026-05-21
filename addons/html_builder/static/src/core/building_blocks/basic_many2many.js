import { Component, t, useProps } from "@odoo/owl";
import { basicContainerBuilderComponentProps } from "../utils";
import { SelectMany2X } from "./select_many2x";

export class BasicMany2Many extends Component {
    static components = { SelectMany2X };
    static template = "html_builder.BasicMany2Many";

    props = useProps({
        ...basicContainerBuilderComponentProps,
        model: t.string(),
        fields: t.array(t.string()).optional(),
        domain: t.array().optional(),
        limit: t.number().optional(),
        selection: t.array(t.object()),
        setSelection: t.function(),
        create: t.function().optional(),
        displayNameField: t.string().optional("display_name"),
        message: t.string().optional(),
    });

    select(entry) {
        this.props.setSelection([...this.props.selection, entry]);
    }
    unselect(id) {
        this.props.setSelection([...this.props.selection.filter((item) => item.id !== id)]);
    }
}
