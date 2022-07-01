/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { PivotArchParser } from "@web/views/pivot/pivot_arch_parser";
import { PivotController } from "./pivot_controller";
import { PivotModel } from "@web/views/pivot/pivot_model";
import { PivotRenderer } from "@web/views/pivot/pivot_renderer";
import { PivotSearchModel } from "./pivot_search_model";

const viewRegistry = registry.category("views");

export const pivotView = {
    type: "pivot",
    display_name: _lt("Pivot"),
    icon: "oi oi-view-pivot",
    multiRecord: true,
    Controller: PivotController,
    Renderer: PivotRenderer,
    Model: PivotModel,
    ArchParser: PivotArchParser,
    SearchModel: PivotSearchModel,
    searchMenuTypes: ["filter", "groupBy", "comparison", "favorite"],
    buttonTemplate: "web.PivotView.Buttons",

    props: (genericProps, view) => {
        let modelParams = {};
        if (genericProps.state) {
            modelParams.data = genericProps.state.data;
            modelParams.metaData = genericProps.state.metaData;
        } else {
            const { arch, additionalMeasures, fields, resModel } = genericProps;

            // parse arch
            const archInfo = new view.ArchParser().parse(arch);

            if (!archInfo.activeMeasures.length || archInfo.displayQuantity) {
                archInfo.activeMeasures.unshift("__count");
            }

            modelParams.metaData = {
                activeMeasures: archInfo.activeMeasures,
                additionalMeasures: additionalMeasures,
                colGroupBys: archInfo.colGroupBys,
                defaultOrder: archInfo.defaultOrder,
                disableLinking: Boolean(archInfo.disableLinking),
                fields: fields,
                fieldAttrs: archInfo.fieldAttrs,
                resModel: resModel,
                rowGroupBys: archInfo.rowGroupBys,
                title: archInfo.title || _lt("Untitled"),
                widgets: archInfo.widgets,
            };
        }

        return {
            ...genericProps,
            Model: view.Model,
            modelParams,
            Renderer: view.Renderer,
            buttonTemplate: view.buttonTemplate,
        };
    },
};

viewRegistry.add("pivot", pivotView);
