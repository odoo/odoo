import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";
import { isInsideSocialSnippet } from "@website/builder/plugins/utils";

export class WebsiteFontAwesomeOption extends BaseOptionComponent {
    static id = "font_awesome_option";
    static template = "website.FontAwesomeOption";

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => {
            const isInSocialSnippet = isInsideSocialSnippet(editingElement);
            return {
                showBackground: !isInSocialSnippet,
                showSize: !isInSocialSnippet,
            };
        });
    }
}

registry.category("website-options").add(WebsiteFontAwesomeOption.id, WebsiteFontAwesomeOption);
