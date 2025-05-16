import { BaseOptionComponent } from "@html_builder/core/utils";
import { BorderConfigurator } from "@website/temp/plugins/border_configurator_option";
import { ShadowOption } from "@website/temp/plugins/shadow_option";
import { WebsiteBackgroundOption } from "@website/website_builder/plugins/options/background_option";

// TODO: BorderConfigurator and ShadowOption directly in BaseOptionComponent ?
export class MediaListItemOption extends BaseOptionComponent {
    static template = "website.MediaListItemOption";
    static components = {
        BorderConfigurator,
        ShadowOption,
        WebsiteBackgroundOption,
    };
    static props = {};
}
