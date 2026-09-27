import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { registry } from "@web/core/registry";
export class FloatingBlocksBlockOption extends BaseOptionComponent {
    static id = "floating_blocks_block_option";
    static template = "website.FloatingBlocksBlockOption";
}

registry.category("website-options").add(FloatingBlocksBlockOption.id, FloatingBlocksBlockOption);
