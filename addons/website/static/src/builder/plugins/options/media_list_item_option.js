import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { WebsiteBackgroundOption } from "@website/builder/plugins/options/background_option";
import { registry } from "@web/core/registry";
import { WebsiteBorderConfigurator } from "@website/builder/plugins/options/website_border_configurator_option";

export class MediaListItemOption extends BaseOptionComponent {
    static id = "media_list_item_option";
    static template = "website.MediaListItemOption";
    static components = {
        WebsiteBackgroundOption,
        WebsiteBorderConfigurator,
    };

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            hasImage: !!editingElement.querySelector(".s_media_list_img_wrapper"),
        }));
    }
}

registry.category("website-options").add(MediaListItemOption.id, MediaListItemOption);
