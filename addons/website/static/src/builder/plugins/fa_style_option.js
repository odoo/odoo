import { BaseOptionComponent } from "@html_builder/core/utils";
import { socialMediaElementsSelector } from "@html_builder/plugins/image/replace_media_option";

export class FaStyleOption extends BaseOptionComponent {
    static template = "website.FaStyleOption";
    static selector = "span.fa, i.fa";
    static exclude = `[data-oe-xpath], ${socialMediaElementsSelector}`;
    static name = "faStyleOption";
}
