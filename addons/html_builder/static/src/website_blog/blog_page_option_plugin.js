import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

class BlogPageOption extends Plugin {
    static id = "blogPageOption";
    resources = {
        builder_options: [
            {
                template: "website_blog.BlogPageOption",
                selector: "main:has(#o_wblog_post_main)",
                editableOnly: false,
                title: _t("Blog Page"),
                groups: ["website.group_website_designer"],
            },
        ],
    };
}

registry.category("website-plugins").add(BlogPageOption.id, BlogPageOption);
