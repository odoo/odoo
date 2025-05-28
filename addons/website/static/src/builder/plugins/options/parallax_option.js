import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
export class ParallaxOption extends BaseOptionComponent {
    static template = "website.ParallaxOption";
    static props = {};

    setup() {
        super.setup();
        this.state = useDomState((el) => ({
            InDialog: el.closest('.modal[role="dialog"]'),
        }));
    }
}
