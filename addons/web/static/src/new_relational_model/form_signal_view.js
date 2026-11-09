import { registry } from "@web/core/registry";
import { NewRelationalModel } from "./new_relational_model";
import { FormSignalArchParser } from "./form_signal_arch_parser";
import { FormSignalController } from "./form_signal_controller";
import { FormSignalRenderer } from "./form_signal_renderer";

/**
 * A form view on top of the record store, kept as small as possible:
 *
 * - the arch parser turns the arch into a tree of plain nodes;
 * - the model (NewRelationalModel) loads and saves the record;
 * - the controller wires the model to the action (buttons, pager, breadcrumbs);
 * - the renderer walks the tree and renders the fields.
 *
 * Use it with `js_class="form_signal"` on a form arch.
 */
export const formSignalView = {
    type: "form",
    searchMenuTypes: [],
    Controller: FormSignalController,
    Renderer: FormSignalRenderer,
    ArchParser: FormSignalArchParser,
    Model: NewRelationalModel,

    props: (genericProps, view) => ({
        ...genericProps,
        Model: view.Model,
        Renderer: view.Renderer,
        archInfo: new view.ArchParser().parse(genericProps.arch),
    }),
};

registry.category("views").add("form_signal", formSignalView);
