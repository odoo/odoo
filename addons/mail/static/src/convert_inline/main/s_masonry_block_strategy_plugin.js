import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";

const BLOCK_SELECTOR =
    ":scope > [data-name='Block'], :scope > .o_masonry_grid_container > .row > [data-name='Block']";

export class MasonryStrategyPlugin extends Plugin {
    static id = "masonryStrategy";
    static dependencies = ["mosaicStrategy"];
    resources = {
        mosaic_cells_providers_processors: this.provideMosaicCells.bind(this),
    };

    getCells(referenceNode) {
        return [...referenceNode.querySelectorAll(BLOCK_SELECTOR)];
    }

    provideMosaicCells(cellsProviders, defaultEmailNodeArguments, { referenceNode }) {
        if (
            !referenceNode.querySelector(BLOCK_SELECTOR) ||
            !referenceNode.closest(".s_masonry_block")
        ) {
            return cellsProviders;
        }
        cellsProviders.push(() => this.getCells(referenceNode));
        return cellsProviders;
    }
}

registry
    .category("mail-html-conversion-core-plugins")
    .add(MasonryStrategyPlugin.id, MasonryStrategyPlugin);
