import { useDomState } from "@html_builder/core/utils";
import { FontAwesomeOption } from "@html_builder/plugins/font_awesome_option";

export class WebsiteFontAwesomeOption extends FontAwesomeOption {
    static template = "website.WebsiteFontAwesomeOption";
    static selector = "span.fa, i.fa, .social_media_img";
    static exclude = "[data-oe-xpath]";
    setup() {
        super.setup();
        this.state = useDomState((editingElement) => {
            const hasRestrictedClass =
                editingElement.closest(".s_social_media") || editingElement.closest(".s_share");
            return {
                showBackground: !hasRestrictedClass,
                showBorder: !hasRestrictedClass,
                showSize: !hasRestrictedClass,
            };
        });
    }
}
