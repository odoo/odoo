/** @odoo-module **/

import { registry } from "@web/core/registry";
import { FormRenderer } from "./form_renderer";
import { RelationalModel } from "../basic_relational_model";
import { FormArchParser } from "./form_arch_parser";
import { FormController } from "./form_controller";
import { FormCompiler } from "./form_compiler";

export const formView = {
    type: "form",
    display_name: "Form",
    multiRecord: false,
    display: { controlPanel: { ["top-right"]: false } },
    searchMenuTypes: [],
    Controller: FormController,
    Renderer: FormRenderer,
    ArchParser: FormArchParser,
    Model: RelationalModel,
    Compiler: FormCompiler,
    buttonTemplate: "web.FormView.Buttons",

    props: (genericProps, view) => {
        const { ArchParser } = view;
        const { arch, fields } = genericProps;
        const archInfo = new ArchParser().parse(arch, fields);

        return {
            ...genericProps,
            Model: view.Model,
            Renderer: view.Renderer,
            buttonTemplate: view.buttonTemplate,
            Compiler: view.Compiler,
            archInfo,
        };
    },
};

registry.category("views").add("form", formView);
