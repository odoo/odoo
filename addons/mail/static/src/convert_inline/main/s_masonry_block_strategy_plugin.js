import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";

export class MasonryStrategyPlugin extends Plugin {
    static id = "masonryStrategy";
    static dependencies = ["mosaicStrategy"];
    resources = {
        mosaic_cells_providers_processors: this.provideMosaicCells.bind(this),
    };

    provideMosaicCells(cellsProviders, defaultEmailNodeArguments, { referenceNode, parentEmailNode }) {

    }
}

registry
    .category("mail-html-conversion-core-plugins")
    .add(MasonryStrategyPlugin.id, MasonryStrategyPlugin);
