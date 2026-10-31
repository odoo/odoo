import { useDomState } from "@html_builder/core/utils";
import { ImageAndIconOption } from "@html_builder/plugins/image/image_and_icon_option";
import { registry } from "@web/core/registry";
import { isInsideSocialSnippet } from "@website/builder/plugins/utils";

export class WebsiteImageAndIconOption extends ImageAndIconOption {
    static id = "image_and_icon_option";
    static template = "website.ImageAndIconOption";

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

registry.category("website-options").add(WebsiteImageAndIconOption.id, WebsiteImageAndIconOption);
