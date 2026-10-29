import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { BackgroundShapeOption } from "@html_builder/plugins/background_option/background_shape_option";
import { WebsiteBackgroundOption } from "@website/builder/plugins/options/background_option";
import { registry } from "@web/core/registry";

export class ReferencesCarouselItemOption extends BaseOptionComponent {
    static id = "references_carousel_item_option";
    static template = "website.ReferencesCarouselItemOption";
    static components = {
        WebsiteBackgroundOption,
        BackgroundShapeOption,
    };
}

registry
    .category("website-options")
    .add(ReferencesCarouselItemOption.id, ReferencesCarouselItemOption);
