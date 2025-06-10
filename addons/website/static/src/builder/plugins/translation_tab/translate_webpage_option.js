import { BaseOptionComponent } from "@html_builder/core/utils";

export class TranslateWebpageOption extends BaseOptionComponent {
    static template = "website.TranslateWebpageOption";
    static props = {
        translationState: Object,
    };
}
