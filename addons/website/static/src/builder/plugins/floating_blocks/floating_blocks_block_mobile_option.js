import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { isMobileView } from "@html_builder/utils/utils";

export class FloatingBlocksBlockMobileOption extends BaseOptionComponent {
    static template = "website.FloatingBlocksBlockMobileOption";
    static props = {};
    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            isMobileView: isMobileView(editingElement),
        }));
    }
}
