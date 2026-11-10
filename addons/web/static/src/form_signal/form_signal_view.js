import { registry } from "@web/core/registry";
import { FormSignalController } from "./form_signal_controller";
import { FormSignalModel } from "./form_signal_model";
import { FormSignalRenderer } from "./form_signal_renderer";

/**
 * A minimal form view on top of the record store:
 *
 * - the model loads one record into the store, and saves it;
 * - the controller creates the model, and adds a save button;
 * - the renderer displays the fields of the arch, as a flat list.
 *
 * Use it with `js_class="form_signal"` on a form arch.
 */
export const formSignalView = {
    type: "form",
    Controller: FormSignalController,
    Model: FormSignalModel,
    Renderer: FormSignalRenderer,

    props: (genericProps, view) => ({
        ...genericProps,
        Model: view.Model,
        Renderer: view.Renderer,
        fieldNames: getFieldNames(genericProps.arch),
    }),
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

registry.category("views").add("form_signal", formSignalView);
