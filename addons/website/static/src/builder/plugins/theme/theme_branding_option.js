import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { _t } from "@web/core/l10n/translation";

export class ThemeBrandingOption extends BaseOptionComponent {
    static template = "website.ThemeBrandingOption";
    // The block's title: `getThemeOptionBlock` can't set it on an existing element
    static title = _t("Website Identification");

    setup() {
        super.setup();
        this.state = useDomState((el) => ({
            faviconSrc: el.dataset.faviconSrc,
            savedName: el.dataset.savedName,
        }));
    }
}
