import { registry } from "@web/core/registry";
import { buildSpecification } from "../views/view_models";
import { ListModel } from "./list_model";
import { SignalListController } from "./signal_list_controller";
import { SignalListRenderer } from "./signal_list_renderer";

/**
 * A minimal list view on top of the record store:
 *
 * - the model loads a page of records into a store, for the current search;
 * - the controller creates the model, adds the pager and the "New" button,
 *   and opens a record in the form view of the action when it is clicked;
 * - the renderer displays the columns of the arch, as text.
 *
 * Use it with `js_class="signal_list"` on a list arch.
 */
export const signalListView = {
    type: "list",
    // records are not grouped
    searchMenuTypes: ["filter", "favorite"],
    Controller: SignalListController,
    Model: ListModel,
    Renderer: SignalListRenderer,

    props: (genericProps, view) => {
        const { arch, fields, resModel } = genericProps;
        const columns = getColumns(arch, fields);
        return {
            ...genericProps,
            Model: view.Model,
            Renderer: view.Renderer,
            relatedModels: genericProps.relatedModels || { [resModel]: { fields } },
            columns,
            specification: buildSpecification(
                fields,
                columns.map((column) => column.name)
            ),
            limit: genericProps.limit || parseInt(arch.getAttribute("limit") || "80", 10),
        };
    },
};

/**
 * The columns of the arch: its fields, without the ones that are always
 * hidden (`column_invisible="1"`) or hidden by default (`optional="hide"`).
 *
 * @param {Element} arch
 * @param {Record<string, any>} fields
 * @returns {{ name: string; string: string; field: any }[]}
 */
function getColumns(arch, fields) {
    const columns = [];
    for (const el of arch.children) {
        if (el.tagName !== "field") {
            continue;
        }
        const isHidden =
            ["1", "True"].includes(el.getAttribute("column_invisible")) ||
            el.getAttribute("optional") === "hide";
        if (isHidden) {
            continue;
        }
        const name = el.getAttribute("name");
        const field = fields[name];
        const hasLabel = !["1", "True"].includes(el.getAttribute("nolabel"));
        columns.push({
            name,
            string: hasLabel ? el.getAttribute("string") || field.string : "",
            field,
        });
    }
    return columns;
}

registry.category("views").add("signal_list", signalListView);
