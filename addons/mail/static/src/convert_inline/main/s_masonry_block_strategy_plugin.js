import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { assignDefaultElementOptions } from "../core/render_models";
import { StyleInfo } from "../core/style_models";

const ROW_SELECTOR = `.s_masonry_block > .container > .row`;
const IMAGE_CELL_SELECTOR = `[data-name='Block']`;
const GRID_CELL_SELECTOR = `.o_masonry_grid_container > .row > [data-name='Block']`;

export class MasonryStrategyPlugin extends Plugin {
    static id = "masonryStrategy";
    static dependencies = ["mosaicStrategy", "rules", "style", "tableStrategy"];
    resources = {
        mosaic_cells_providers_processors: this.provideMosaicCells.bind(this),
        mosaic_cells_element_options_providers_processors:
            this.provideCellElementOptions.bind(this),
    };

    getCells(referenceNode) {
        return [
            ...referenceNode.querySelectorAll(
                `:scope > ${IMAGE_CELL_SELECTOR}, :scope > ${GRID_CELL_SELECTOR}`
            ),
        ];
    }

    provideMosaicCells(cellsProviders, defaultEmailNodeArguments, { referenceNode }) {
        if (
            !referenceNode.querySelector(
                `:scope > ${IMAGE_CELL_SELECTOR}, :scope > ${GRID_CELL_SELECTOR}`
            ) ||
            !referenceNode.matches(ROW_SELECTOR)
        ) {
            return cellsProviders;
        }
        cellsProviders.push(() => this.getCells(referenceNode));
        return cellsProviders;
    }

    provideCellElementOptions(options, cellMeasure) {
        const { referenceNode, emailNode } = cellMeasure;
        if (
            !referenceNode ||
            !referenceNode.matches(
                `${ROW_SELECTOR} > ${IMAGE_CELL_SELECTOR}, ${ROW_SELECTOR} > ${GRID_CELL_SELECTOR}`
            )
        ) {
            return options;
        }
        const cellStyleInfo = StyleInfo.from({ "vertical-align": "middle" });
        const styleInfo = emailNode.layout.getRef().styleInfo;
        const backgroundStyleInfo = this.getCellBackgroundStyleInfo(styleInfo, referenceNode);
        const borderStyleInfo = this.getCellBorderStyleInfo(styleInfo, referenceNode);
        for (const propertyName of [...backgroundStyleInfo.keys(), ...borderStyleInfo.keys()]) {
            styleInfo.removeProperty(propertyName);
        }
        return assignDefaultElementOptions(
            { style: cellStyleInfo.merge(backgroundStyleInfo).merge(borderStyleInfo) },
            options
        );
    }
}

registry
    .category("mail-html-conversion-core-plugins")
    .add(MasonryStrategyPlugin.id, MasonryStrategyPlugin);
