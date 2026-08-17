import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { assignDefaultElementOptions } from "../core/render_models";

const ROW_SELECTOR = `.s_comparisons > .container > .row`;
const COL_SELECTOR = `[data-name='Plan']`;
const BODY_CELL_SELECTOR = `.card-body`;
const FOOTER_CELL_SELECTOR = `.card-footer`;
const CELL_SELECTOR = `${COL_SELECTOR} > .card > :is(${BODY_CELL_SELECTOR}, ${FOOTER_CELL_SELECTOR})`;

export class ComparisonsStrategyPlugin extends Plugin {
    static id = "comparisonsStrategy";
    static dependencies = ["mosaicStrategy"];
    resources = {
        mosaic_cells_providers_processors: this.provideMosaicCells.bind(this),
        mosaic_cells_element_options_providers_processors:
            this.provideCellElementOptions.bind(this),
    };

    // TODO EGGMAIL: on_measure_reference_content_handlers
    // call getBoundingClientRect to cache the mobile value

    getCells(referenceNode) {
        return [...referenceNode.querySelectorAll(`:scope > ${CELL_SELECTOR}`)];
    }

    provideMosaicCells(cellsProviders, defaultEmailNodeArguments, { referenceNode }) {
        if (
            !referenceNode.querySelector(`:scope > ${CELL_SELECTOR}`) ||
            !referenceNode.matches(ROW_SELECTOR)
        ) {
            return cellsProviders;
        }
        cellsProviders.push(() => this.getCells(referenceNode));
        return cellsProviders;
    }

    provideCellElementOptions(options, cellMeasure) {
        const { referenceNode } = cellMeasure;
        if (!referenceNode || !referenceNode.matches(`${ROW_SELECTOR} > ${CELL_SELECTOR}`)) {
            return options;
        }
        if (referenceNode.matches(BODY_CELL_SELECTOR)) {
            options = assignDefaultElementOptions({ style: { "vertical-align": "top" } }, options);
        } else if (referenceNode.matches(FOOTER_CELL_SELECTOR)) {
            options = assignDefaultElementOptions(
                { style: { "vertical-align": "bottom" } },
                options
            );
        }
        return options;
    }
}

registry
    .category("mail-html-conversion-core-plugins")
    .add(ComparisonsStrategyPlugin.id, ComparisonsStrategyPlugin);
