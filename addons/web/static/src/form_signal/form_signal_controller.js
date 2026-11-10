import { Component, t, useProps } from "@odoo/owl";
import { useModel } from "@web/model/model";
import { Layout } from "@web/search/layout";
import { standardViewProps } from "@web/views/standard_view_props";

export class FormSignalController extends Component {
    static template = "web.FormSignalController";
    static components = { Layout };

    props = useProps({
        ...standardViewProps,
        Model: t.function(),
        Renderer: t.function(),
        fieldNames: t.array(t.string()),
    });

    model = useModel(this.props.Model, {
        resModel: this.props.resModel,
        resId: this.props.resId || false,
        fields: this.props.fields,
        fieldNames: this.props.fieldNames,
        context: this.props.context,
    });
}
