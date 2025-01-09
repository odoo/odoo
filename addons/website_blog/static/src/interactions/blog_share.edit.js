import { registry } from "@web/core/registry";
import { BlogShare } from "./blog_share";

const BlogShareEdit = I => class extends I {
    dynamicContent = {
        ...this.dynamicContent,
        _root: {},
    };
};

registry
    .category("public.interactions.edit")
    .add("website_blog.blog_share", {
        Interaction: BlogShare,
        mixin: BlogShareEdit,
        isAbstract: true,
    });
