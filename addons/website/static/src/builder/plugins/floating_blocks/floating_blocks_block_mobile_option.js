import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";

export class FloatingBlocksBlockMobileOption extends BaseOptionComponent {
    static id = "floating_blocks_block_mobile_option";
    static template = "website.FloatingBlocksBlockMobileOption";
    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            isMobileView: this.env.editor.config.isMobileView(editingElement),
        }));
    }
}

registry
    .category("website-options")
    .add(FloatingBlocksBlockMobileOption.id, FloatingBlocksBlockMobileOption);
