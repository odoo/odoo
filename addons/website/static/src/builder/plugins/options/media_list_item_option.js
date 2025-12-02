import { BaseOptionComponent } from "@html_builder/core/utils";
import { WebsiteBackgroundOption } from "@website/builder/plugins/options/background_option";
import { registry } from "@web/core/registry";

export class MediaListItemOption extends BaseOptionComponent {
    static id = "media_list_item_option";
    static template = "website.MediaListItemOption";
    static components = {
        WebsiteBackgroundOption,
    };
}

registry.category("builder-options").add(MediaListItemOption.id, MediaListItemOption);
