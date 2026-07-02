import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export class FloatingBlocksBlockOptionPlugin extends Plugin {
    static id = "floatingBlocksBlockOptionPlugin";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        dropzone_selectors: [
            // Lock block-items within the snippet
            {
                selector: ".s_floating_blocks .s_floating_blocks_block",
                dropLockWithin: ".s_floating_blocks",
                dropNear: ".s_floating_blocks .s_floating_blocks_block",
            },
        ],
        remove_disabled_reason_providers: (el) => {
            if (el.matches(".s_floating_blocks_block:only-child")) {
                return _t("You cannot remove the last item.");
            }
        },
    };
}

registry
    .category("website-plugins")
    .add(FloatingBlocksBlockOptionPlugin.id, FloatingBlocksBlockOptionPlugin);
