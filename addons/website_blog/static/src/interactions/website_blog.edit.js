import { registry } from "@web/core/registry";
import { WebsiteBlog } from "./website_blog";

const WebsiteBlogEdit = (I) =>
    class extends I {
        dynamicContent = {
            ".o_sticky_reactive": {
                "t-att-style": () => ({
                    top: `${this.position || this.defaultPosition}px`,
                    transition: "top 0.2s",
                }),
            },
        };
    };

registry.category("public.interactions.edit").add("website_blog.website_blog", {
    Interaction: WebsiteBlog,
    mixin: WebsiteBlogEdit,
});
