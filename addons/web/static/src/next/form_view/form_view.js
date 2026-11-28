import { registry } from "@web/core/registry";
import { RelModel } from "../rel_model/rel_model";
import { compileFormArch } from "./form_compiler";
import { FormController } from "./form_controller";
import { FormRenderer } from "./form_renderer";

/**
 * The form view on top of the record store:
 *
 * - the arch is compiled into a template, and describes the fields to load;
 * - the model loads one record into a store, saves it and discards its changes
 *   (see `RelModel`);
 * - the controller creates the model, and adds the save and discard buttons;
 * - the renderer displays the record with the compiled template.
 *
 * Use it with `js_class="next_form"` on a form arch.
 */
export const formView = {
    type: "form",
    searchMenuTypes: [],
    Controller: FormController,
    Model: RelModel,
    Renderer: FormRenderer,

    props: (genericProps, view) => {
        const { arch, fields, resModel } = genericProps;
        const relatedModels = genericProps.relatedModels || { [resModel]: { fields } };
        return {
            ...genericProps,
            Model: view.Model,
            Renderer: view.Renderer,
            relatedModels,
            archInfo: compileFormArch(arch, { resModel, relatedModels }),
        };
    },
};

registry.category("views").add("next_form", formView);
