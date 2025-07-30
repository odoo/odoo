import { BaseOptionComponent } from "@html_builder/core/utils";
import { _t } from "@web/core/l10n/translation";

export class ThemeAdvancedOption extends BaseOptionComponent {
    static template = "website.ThemeAdvancedOption";
    static props = {
        grays: Object,
    };

    getGrayTitle(grayCode) {
        return _t("Gray %(grayCode)s", { grayCode });
    }
}
