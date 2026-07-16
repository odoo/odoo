import { registry } from "@web/core/registry";
import { WebsiteBlog } from "./website_blog";
import { omit } from "@web/core/utils/objects";

const WebsiteBlogEdit = (I) =>
    class extends I {
        dynamicContent = omit(
            this.dynamicContent,
            ".o_wblog_sheet_trigger",
            ".o_wblog_next_button"
        );
    };

registry.category("public.interactions.edit").add("website_blog.website_blog", {
    Interaction: WebsiteBlog,
    mixin: WebsiteBlogEdit,
});
