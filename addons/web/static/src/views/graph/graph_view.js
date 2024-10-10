import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { GraphArchParser } from "./graph_arch_parser";
import { GraphController } from "./graph_controller";
import { GraphModel } from "./graph_model";
import { GraphRenderer } from "./graph_renderer";
import { GraphSearchModel } from "./graph_search_model";

const viewRegistry = registry.category("views");

export class GraphView {
    static type = "graph";
    static Controller = GraphController; // -> Component
    static SearchModel = GraphSearchModel;
    static ArchParser = GraphArchParser;
    static Model = GraphModel;
    static Renderer = GraphRenderer;
    static searchMenuTypes = ["filter", "groupBy", "comparison", "favorite"];
    static buttonTemplate = "web.GraphView.Buttons";

    getComponentProps(genericProps) {
        let modelParams;
        if (genericProps.state) {
            modelParams = genericProps.state.metaData;
        } else {
            const { arch, fields, resModel } = genericProps;
            const parser = new this.constructor.ArchParser();
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
            Model: this.constructor.Model,
            Renderer: this.constructor.Renderer,
            buttonTemplate: this.constructor.buttonTemplate,
        };
    }
}

viewRegistry.add("graph", GraphView);
