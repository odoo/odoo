import { useBuilderComponents } from "@html_builder/core/utils";
import { BackgroundOption } from "@html_builder/plugins/background_option/background_option";

export class ParallaxOption extends BackgroundOption {
    static template = "website.ParallaxOption";
    static props = {};
    setup() {
        super.setup();
        useBuilderComponents();
    }
}
