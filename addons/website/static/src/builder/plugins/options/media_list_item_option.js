import { BaseOptionComponent } from "@html_builder/core/utils";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";
import { ShadowOption } from "@html_builder/plugins/shadow_option";
import { BaseWebsiteBackgroundOption } from "@website/builder/plugins/options/background_option";

// TODO: BorderConfigurator and ShadowOption directly in BaseOptionComponent ?
export class MediaListItemOption extends BaseOptionComponent {
    static template = "website.MediaListItemOption";
    static selector = ".s_media_list_item";
    static components = {
        BorderConfigurator,
        ShadowOption,
        BaseWebsiteBackgroundOption,
    };
}
