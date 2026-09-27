import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class WebsiteHrRecruitmentFloatingSnippetsPlugin extends Plugin {
    static id = "websiteHrRecruitmentFloatingSnippets";

    resources = {
        floating_snippet_scope_providers: [
            withSequence(35, {
                label: _t("This job"),
                containerSelector: ".js_hr_recruitment [data-oe-field='website_description']",
                isThisPage: true,
            }),
            withSequence(30, {
                label: _t("This page"),
                containerSelector: "#oe_structure_hr_recruitment_index_bottom",
                isThisPage: true,
            }),
            withSequence(5, {
                label: _t("All jobs"),
                containerSelector:
                    "#oe_structure_hr_recruitment_index_2, #oe_structure_hr_recruitment_index_1, #oe_structure_hr_recruitment_index_0",
            }),
        ],
    };
}

registry
    .category("website-plugins")
    .add(WebsiteHrRecruitmentFloatingSnippetsPlugin.id, WebsiteHrRecruitmentFloatingSnippetsPlugin);
