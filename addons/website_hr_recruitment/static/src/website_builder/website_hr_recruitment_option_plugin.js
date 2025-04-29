import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

class WebsiteHrRecruitmentPageOption extends Plugin {
    static id = "websiteHrRecruitmentPageOption";
    resources = {
        builder_options: [
            {
                template: "website_hr_recruitment.JobsPageOption",
                selector: "main:has(.o_website_hr_recruitment_jobs_list)",
                title: _t("Jobs Page"),
                editableOnly: false,
                groups: ["website.group_website_designer"],
            },
        ],
    };
}

registry
    .category("website-plugins")
    .add(WebsiteHrRecruitmentPageOption.id, WebsiteHrRecruitmentPageOption);
