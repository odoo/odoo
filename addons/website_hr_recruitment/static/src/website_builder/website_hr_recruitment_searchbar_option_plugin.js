import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

class HrRecruitmentSearchbarOptionPlugin extends Plugin {
    static id = "hrRecruitmentSearchbarOption";

    resources = {
        searchbar_option_display_items: {
            label: _t("Description"),
            dataAttribute: "displayDescription",
            dependency: "search_jobs_opt",
        },
    };
}

registry
    .category("website-plugins")
    .add(HrRecruitmentSearchbarOptionPlugin.id, HrRecruitmentSearchbarOptionPlugin);
