import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";

export class ComparisonsStrategyPlugin extends Plugin {
    static id = "comparisonsStrategy";
    static dependencies = ["mosaicStrategy"];
    resources = {
        element_layout_analysis_processors: this.analyzeElementLayout.bind(this),
        mosaic_cells_providers_processors: this.provideMosaicCells.bind(this),
    };

    setup() {
        
    }

    getCells(referenceNode) {
        return [
            ...referenceNode.querySelectorAll(
                ":scope > [data-name='Plan'] > .card > :is(.card-body, .card-footer)"
            ),
        ];
    }

    analyzeElementLayout(defaultEmailNodeArguments, { referenceNode, parentEmailNode }) {

    }

    provideMosaicCells(cellsProviders, defaultEmailNodeArguments, { referenceNode }) {
        if (
            !referenceNode.querySelector(":scope > [data-name='Plan']") ||
            !referenceNode.closest(".s_comparisons")
        ) {
            return cellsProviders;
        }
        cellsProviders.push(() => this.getCells(referenceNode));
        return cellsProviders;
    }
}

registry
    .category("mail-html-conversion-core-plugins")
    .add(ComparisonsStrategyPlugin.id, ComparisonsStrategyPlugin);
