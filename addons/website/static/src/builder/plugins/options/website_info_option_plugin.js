import { BaseOptionComponent } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class InfoPageOption extends BaseOptionComponent {
    static template = "website.InfoPageOption";
    static selector = "main:has(.o_website_info)";
    static title = _t("Info Page");
    static editableOnly = false;
    static groups = ["website.group_website_designer"];
}

class WebsiteInfoPageOption extends Plugin {
    static id = "websiteInfoPageOption";
    resources = {
        builder_options: [InfoPageOption],
    };
}

registry.category("website-plugins").add(WebsiteInfoPageOption.id, WebsiteInfoPageOption);
