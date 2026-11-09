import { Component, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { standardViewProps } from "@web/views/standard_view_props";

export class FormSignalController extends Component {
    static template = "web.FormSignalView";
    static components = { Layout };

    props = useProps(standardViewProps);
}

export const formSignalView = {
    type: "form",
    Controller: FormSignalController,
};

registry.category("views").add("form_signal", formSignalView);
