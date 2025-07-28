import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { isMobileView } from "@html_builder/utils/utils";

export class FloatingBlocksBlockMobileOption extends BaseOptionComponent {
    static template = "website.FloatingBlocksBlockMobileOption";
    static selector = ".s_floating_blocks .s_floating_blocks_block";
    static applyTo = ".container-fluid";
    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            isMobileView: isMobileView(editingElement),
        }));
    }
}
