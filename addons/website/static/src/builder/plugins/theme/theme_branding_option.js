import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { onWillStart } from "@odoo/owl";

export class ThemeBrandingOption extends BaseOptionComponent {
    static template = "website.ThemeBrandingOption";
    static dependencies = ["themeBranding"];

    setup() {
        super.setup();
        this.branding = this.dependencies.themeBranding;
        onWillStart(() => this.branding.checkSavedFavicon());
    }
}
