import { registry } from "@web/core/registry";
import { WebsiteBlog } from "./website_blog";
import { pick } from "@web/core/utils/objects";

const WebsiteBlogEdit = (I) =>
    class extends I {
        // Only keep the sticky behavior in edit mode.
        dynamicContent = pick(this.dynamicContent, "_stickyEl", "_root");
    };

registry.category("public.interactions.edit").add("website_blog.website_blog", {
    Interaction: WebsiteBlog,
    mixin: WebsiteBlogEdit,
});
