import { useState } from "@web/owl2/utils";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { _t } from "@web/core/l10n/translation";

export class ThemeAdvancedOption extends BaseOptionComponent {
    static template = "website.ThemeAdvancedOption";
    static dependencies = ["themeTab"];
    setup() {
        super.setup();
        this.grays = useState(this.dependencies.themeTab.getGrays());
    }

    getGrayTitle(grayCode) {
        return _t("Gray %(grayCode)s", { grayCode });
    }
}
