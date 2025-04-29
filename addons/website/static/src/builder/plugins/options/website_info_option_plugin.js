import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

class WebsiteInfoPageOption extends Plugin {
    static id = "websiteInfoPageOption";
    resources = {
        builder_options: [
            {
                template: "website.InfoPageOption",
                selector: "main:has(.o_website_info)",
                title: _t("Info Page"),
                editableOnly: false,
                groups: ["website.group_website_designer"],
            },
        ],
    };
}

registry.category("website-plugins").add(WebsiteInfoPageOption.id, WebsiteInfoPageOption);
