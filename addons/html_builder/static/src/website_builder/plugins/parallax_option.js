import { defaultBuilderComponents } from "@html_builder/core/default_builder_components";
import { BackgroundOption } from "@html_builder/plugins/background_option/background_option";

export class ParallaxOption extends BackgroundOption {
    static template = "website.ParallaxOption";
    static components = {
        ...defaultBuilderComponents,
    };
    static props = {};
}
