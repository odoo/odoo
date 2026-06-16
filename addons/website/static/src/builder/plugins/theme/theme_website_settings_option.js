import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { ImageSize } from "@html_builder/plugins/image/image_size";

export class ThemeWebsiteSettingsOption extends BaseOptionComponent {
    static template = "website.ThemeWebsiteSettingsOption";
    static components = { ImageSize };
}
