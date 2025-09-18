// @ts-check

/** @module @web/views/pivot/pivot_view - Pivot view descriptor registered in the view registry */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { PivotArchParser } from "@web/views/pivot/pivot_arch_parser";
import { PivotModel } from "@web/views/pivot/pivot_model";
import { PivotRenderer } from "@web/views/pivot/pivot_renderer";

import { PivotController } from "./pivot_controller";
import { PivotSearchModel } from "./pivot_search_model";

const viewRegistry = registry.category("views");

/**
 * Pivot view descriptor.
 *
 * Registers the pivot view type with its Controller, Renderer, Model,
 * ArchParser and SearchModel. The `props` factory parses the arch and
 * builds `modelParams` (with `metaData` and optional `data`) consumed
 * by `PivotModel`.
 */
export const pivotView = {
    type: "pivot",
    Controller: PivotController,
    Renderer: PivotRenderer,
    Model: PivotModel,
    ArchParser: PivotArchParser,
    SearchModel: PivotSearchModel,
    searchMenuTypes: ["filter", "groupBy", "favorite"],
    buttonTemplate: "web.PivotView.Buttons",

    /**
     * @param {Object} genericProps - standard view props (arch, fields, resModel, state)
     * @param {Object} view - view descriptor with Model, Renderer, ArchParser
     * @returns {Object} controller props including modelParams with metaData and optional data
     */
    props: (genericProps, view) => {
        const modelParams = {};
        if (genericProps.state) {
            modelParams.data = genericProps.state.data;
            modelParams.metaData = genericProps.state.metaData;
        } else {
            const { arch, fields, resModel } = genericProps;

            // parse arch
            const archInfo = new view.ArchParser().parse(arch);

            if (!archInfo.activeMeasures.length || archInfo.displayQuantity) {
                archInfo.activeMeasures.unshift("__count");
            }

            modelParams.metaData = {
                activeMeasures: archInfo.activeMeasures,
                colGroupBys: archInfo.colGroupBys,
                defaultOrder: archInfo.defaultOrder,
                disableLinking: Boolean(archInfo.disableLinking),
                fields: fields,
                fieldAttrs: archInfo.fieldAttrs,
                resModel: resModel,
                rowGroupBys: archInfo.rowGroupBys,
                title: archInfo.title || _t("Untitled"),
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
