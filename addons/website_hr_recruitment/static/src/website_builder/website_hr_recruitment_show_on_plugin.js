import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class WebsiteHrRecruitmentShowOnPlugin extends Plugin {
    static id = "websiteHrRecruitmentShowOn";

    resources = {
        popup_show_on_options: withSequence(60, {
            value: "allJobs",
            label: _t("All jobs"),
            pageSelector: "main:has(.js_hr_recruitment)",
        }),
    };
}

registry
    .category("website-plugins")
    .add(WebsiteHrRecruitmentShowOnPlugin.id, WebsiteHrRecruitmentShowOnPlugin);
