import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { WebsiteBackgroundOption } from "@website/builder/plugins/options/background_option";
import { registry } from "@web/core/registry";

export class LoveReviewOption extends BaseOptionComponent {
    static id = "love_review_option";
    static template = "website.LoveReviewOption";
    static components = {
        WebsiteBackgroundOption,
    };
}

registry.category("website-options").add(LoveReviewOption.id, LoveReviewOption);
