import { useDomState } from "@html_builder/core/utils";
import { ImageAndFaOption } from "@html_builder/plugins/image/image_and_fa_option";
import { registry } from "@web/core/registry";
import { isInsideSocialSnippet } from "@website/builder/plugins/utils";

export class WebsiteImageAndFaOption extends ImageAndFaOption {
    static id = "image_and_fa_option";
    static template = "website.ImageAndFaOption";

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => {
            const isInSocialSnippet = isInsideSocialSnippet(editingElement);
            return {
                isImage: editingElement.tagName === "IMG",
                showBorder: !isInSocialSnippet,
            };
        });
    }
}

registry.category("website-options").add(WebsiteImageAndFaOption.id, WebsiteImageAndFaOption);
