import { BaseOptionComponent } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";
import { AddElementOption } from "@website/builder/plugins/layout_option/add_element_option";

export class FloatingBlocksBlockOption extends BaseOptionComponent {
    static id = "floating_blocks_block_option";
    static template = "website.FloatingBlocksBlockOption";
    static components = { AddElementOption };
}

registry.category("website-options").add(FloatingBlocksBlockOption.id, FloatingBlocksBlockOption);
