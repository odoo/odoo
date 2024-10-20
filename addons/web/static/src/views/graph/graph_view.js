import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { GraphArchParser } from "./graph_arch_parser";
import { GraphController } from "./graph_controller";
import { GraphModel } from "./graph_model";
import { GraphRenderer } from "./graph_renderer";
import { GraphSearchModel } from "./graph_search_model";

const viewRegistry = registry.category("views_new");

export class GraphViewDescription {
    Controller = GraphController; // -> Component
    SearchModel = GraphSearchModel;
    ArchParser = GraphArchParser;
    Model = GraphModel;
    Renderer = GraphRenderer;
    searchMenuTypes = ["filter", "groupBy", "comparison", "favorite"];
    buttonTemplate = "web.GraphView.Buttons";

    getComponentProps(genericProps) {
        let modelParams;
        if (genericProps.state) {
            modelParams = genericProps.state.metaData;
        } else {
            const { arch, fields, resModel } = genericProps;
            const parser = new this.ArchParser();
            const archInfo = parser.parse(arch, fields);
            modelParams = {
                disableLinking: Boolean(archInfo.disableLinking),
                fieldAttrs: archInfo.fieldAttrs,
                fields: fields,
                groupBy: archInfo.groupBy,
                measure: archInfo.measure || "__count",
                viewMeasures: archInfo.measures,
                mode: archInfo.mode || "bar",
                order: archInfo.order || null,
                resModel: resModel,
                stacked: "stacked" in archInfo ? archInfo.stacked : true,
                cumulated: archInfo.cumulated || false,
                cumulatedStart: archInfo.cumulatedStart || false,
                title: archInfo.title || _t("Untitled"),
            };
        }

        return {
            ...genericProps,
            modelParams,
            Model: this.Model,
            Renderer: this.Renderer,
            buttonTemplate: this.buttonTemplate,
        };
    }
}

viewRegistry.add("graph", GraphViewDescription);
