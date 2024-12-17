import { registry } from "@web/core/registry";
import { BlogContentShare } from "./contentshare";

const BlogContentShareEdit = I => class extends I {
    dynamicContent = {
        ...this.dynamicContent,
        "_root": {},
    };
};

registry
    .category("public.interactions.edit")
    .add("website_blog.blog_content_share", {
        Interaction: BlogContentShare,
        mixin: BlogContentShareEdit,
    });
