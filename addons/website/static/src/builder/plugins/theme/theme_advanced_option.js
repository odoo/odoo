import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { _t } from "@web/core/l10n/translation";

export class ThemeAdvancedOption extends BaseOptionComponent {
    static template = "website.ThemeAdvancedOption";

    getHeaderTooltip() {
        return this.isActiveItem("show_header_opt")
            ? _t("Hide header on all pages")
            : _t("Show header on all pages");
    }

    getFooterTooltip() {
        return this.isActiveItem("show_footer_opt")
            ? _t("Hide footer on all pages")
            : _t("Show footer on all pages");
    }
}
