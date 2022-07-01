/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { GraphArchParser } from "./graph_arch_parser";
import { GraphModel } from "./graph_model";
import { GraphController } from "./graph_controller";
import { GraphRenderer } from "./graph_renderer";
import { GraphSearchModel } from "./graph_search_model";

const viewRegistry = registry.category("views");

export const graphView = {
    type: "graph",
    display_name: _lt("Graph"),
    icon: "fa fa-area-chart",
    multiRecord: true,
    Controller: GraphController,
    Renderer: GraphRenderer,
    Model: GraphModel,
    ArchParser: GraphArchParser,
    SearchModel: GraphSearchModel,
    searchMenuTypes: ["filter", "groupBy", "comparison", "favorite"],
    buttonTemplate: "web.GraphView.Buttons",

    props: (genericProps, view) => {
        let modelParams;
        if (genericProps.state) {
            modelParams = genericProps.state.metaData;
        } else {
            const { arch, fields, resModel, additionalMeasures, displayScaleLabels } = genericProps;
            const parser = new view.ArchParser();
            const archInfo = parser.parse(arch, fields);
            modelParams = {
                additionalMeasures: additionalMeasures,
                disableLinking: Boolean(archInfo.disableLinking),
                displayScaleLabels: displayScaleLabels,
                fieldAttrs: archInfo.fieldAttrs,
                fields: fields,
                groupBy: archInfo.groupBy,
                measure: archInfo.measure || "__count",
                mode: archInfo.mode || "bar",
                order: archInfo.order || null,
                resModel: resModel,
                stacked: "stacked" in archInfo ? archInfo.stacked : true,
                title: archInfo.title || _lt("Untitled"),
            };
        }

        return {
            ...genericProps,
            modelParams,
            Model: view.Model,
            Renderer: view.Renderer,
            buttonTemplate: view.buttonTemplate,
        };
    },
};

viewRegistry.add("graph", graphView);
