import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";

export class FloatingBlocksBlockMobileOption extends BaseOptionComponent {
    static template = "website.FloatingBlocksBlockMobileOption";
    static props = {};
    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            isMobileView: this.env.editor.config.isMobileView(editingElement),
        }));
    }
}
