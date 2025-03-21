import { BaseOptionComponent } from "@html_builder/core/utils";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";
import { ShadowOption } from "@html_builder/plugins/shadow_option";
import { WebsiteBackgroundOption } from "@html_builder/website_builder/plugins/options/background_option";

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
