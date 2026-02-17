import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class FloatingBlocksBlockOptionPlugin extends Plugin {
    static id = "floatingBlocksBlockOptionPlugin";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        dropzone_selector: [
            // Lock grid-items within their grid
            {
                selector: ".s_floating_blocks_block_grid .o_grid_item",
                dropLockWithin: ".s_floating_blocks_block_grid",
            },
            // Lock block-items within the snippet
            {
                selector: ".s_floating_blocks .s_floating_blocks_block",
                dropLockWithin: ".s_floating_blocks",
                dropNear: ".s_floating_blocks .s_floating_blocks_block",
            },
        ],
    };
}

registry
    .category("website-plugins")
    .add(FloatingBlocksBlockOptionPlugin.id, FloatingBlocksBlockOptionPlugin);
