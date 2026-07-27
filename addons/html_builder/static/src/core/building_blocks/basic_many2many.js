import { Component, props, t } from "@odoo/owl";
import { SelectMany2X } from "./select_many2x";

export class BasicMany2Many extends Component {
    static template = "html_builder.BasicMany2Many";
    props = props({
        // basicContainerBuilderComponentProps (converted inline)
        id: t.string().optional(),
        applyTo: t.string().optional(),
        preview: t.boolean().optional(),
        inheritedActions: t.array(t.string()).optional(),

        action: t.string().optional(),
        actionParam: t.any().optional(),

        // Shorthand actions.
        classAction: t.any().optional(),
        attributeAction: t.any().optional(),
        dataAttributeAction: t.any().optional(),
        styleAction: t.any().optional(),

        model: t.string(),
        fields: t.array(t.string()).optional(),
        domain: t.array().optional(),
        limit: t.number().optional(),
        selection: t.array(t.object()),
        setSelection: t.function(),
        create: t.function().optional(),
        displayNameField: t.string().optional("display_name"),
    });
    static components = { SelectMany2X };

    select(entry) {
        this.props.setSelection([...this.props.selection, entry]);
    }
    unselect(id) {
        this.props.setSelection([...this.props.selection.filter((item) => item.id !== id)]);
    }
}
