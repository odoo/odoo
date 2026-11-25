import { registry } from "@web/core/registry";
import { buildSpecification } from "../views/view_models";
import { FormModel } from "./form_model";
import { SignalFormController } from "./signal_form_controller";
import { SignalFormRenderer } from "./signal_form_renderer";

/**
 * A minimal form view on top of the record store:
 *
 * - the model loads one record into a store, saves it and discards its changes;
 * - the controller creates the model, and adds the save and discard buttons;
 * - the renderer displays the fields of the arch, as a flat list.
 *
 * Use it with `js_class="signal_form"` on a form arch.
 */
export const signalFormView = {
    type: "form",
    Controller: SignalFormController,
    Model: FormModel,
    Renderer: SignalFormRenderer,

    props: (genericProps, view) => {
        const fieldNames = getFieldNames(genericProps.arch);
        return {
            ...genericProps,
            Model: view.Model,
            Renderer: view.Renderer,
            fieldNames,
            specification: buildSpecification(genericProps.fields, fieldNames),
        };
    },
};

/**
 * Names of the fields of the arch, without the fields of x2many sub-views.
 *
 * @param {Element} arch
 */
function getFieldNames(arch) {
    const names = [...arch.querySelectorAll("field")]
        .filter((el) => !el.parentElement.closest("field"))
        .map((el) => el.getAttribute("name"))
        .filter((name) => name !== "id");
    return [...new Set(names)];
}

registry.category("views").add("signal_form", signalFormView);
