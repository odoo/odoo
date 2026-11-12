import { BaseOptionComponent } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class JobsPageOption extends BaseOptionComponent {
    static template = "website_hr_recruitment.JobsPageOption";
    static selector = "main:has(.o_website_hr_recruitment_jobs_list)";
    static title = _t("Jobs Page");
    static groups = ["website.group_website_designer"];
    static editableOnly = false;
}

class WebsiteHrRecruitmentPageOption extends Plugin {
    static id = "websiteHrRecruitmentPageOption";
    resources = {
        builder_options: [JobsPageOption],
        // The job description's ratings use the same color for active and
        // inactive icons: only the hollow glyph tells them apart.
        hollow_rating_selectors: ".s_rating:has(.s_rating_inactive_icons.text-primary)",
    };
}

registry
    .category("website-plugins")
    .add(WebsiteHrRecruitmentPageOption.id, WebsiteHrRecruitmentPageOption);
