import { Component, t, useProps } from "@odoo/owl";
import { useModel } from "@web/model/model";
import { Layout } from "@web/search/layout";
import { standardViewProps } from "@web/views/standard_view_props";

export class FormController extends Component {
    static template = "web.next.FormController";
    static components = { Layout };

    props = useProps({
        ...standardViewProps,
        Model: t.function(),
        Renderer: t.function(),
        /** @type {any} see `FormArchInfo` */
        archInfo: t.object(),
    });

    model = useModel(this.props.Model, {
        resModel: this.props.resModel,
        resId: this.props.resId || false,
        specification: this.props.archInfo.specification,
        relatedModels: this.props.relatedModels,
        context: this.props.context,
    });
}
