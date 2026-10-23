import { registry } from "@web/core/registry";
import { WebsiteBlog, COMPATIBILITY_SHARE_SELECTOR } from "./website_blog";
import { omit } from "@web/core/utils/objects";

const WebsiteBlogEdit = (I) =>
    class extends I {
        // Only keep the sticky behavior from StickyBelowHeader interaction
        dynamicContent = omit(
            this.dynamicContent,
            ".o_wblog_sheet_trigger",
            ".o_wblog_next_button",
            COMPATIBILITY_SHARE_SELECTOR
        );
    };

registry.category("public.interactions.edit").add("website_blog.website_blog", {
    Interaction: WebsiteBlog,
    mixin: WebsiteBlogEdit,
});
