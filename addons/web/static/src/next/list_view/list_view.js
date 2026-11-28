import { registry } from "@web/core/registry";
import { RelModel } from "../rel_model/rel_model";
import { buildSpecification, parseListColumns } from "../views/field_nodes";
import { ListController } from "./list_controller";
import { ListRenderer } from "./list_renderer";

/**
 * The list view on top of the record store:
 *
 * - the arch describes the columns, and the fields to load;
 * - the model loads a page of records into a store, for the current search
 *   (see `RelModel`);
 * - the controller creates the model, adds the pager and the "New" button,
 *   and opens a record in the form view of the action when it is clicked;
 * - the renderer displays the records with the components of their fields,
 *   like the list of an x2many field.
 *
 * Use it with `js_class="next_list"` on a list arch.
 */
export const listView = {
    type: "list",
    // records are not grouped
    searchMenuTypes: ["filter", "favorite"],
    Controller: ListController,
    Model: RelModel,
    Renderer: ListRenderer,

    props: (genericProps, view) => {
        const { arch, fields, resModel } = genericProps;
        const relatedModels = genericProps.relatedModels || { [resModel]: { fields } };
        const columns = parseListColumns(arch, resModel, relatedModels);
        return {
            ...genericProps,
            Model: view.Model,
            Renderer: view.Renderer,
            relatedModels,
            columns,
            specification: buildSpecification(columns),
            limit: genericProps.limit || parseInt(arch.getAttribute("limit") || "80", 10),
        };
    },
};

registry.category("views").add("next_list", listView);
