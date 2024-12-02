import { registry } from "@web/core/registry";
import { BlogContentShare } from "./contentshare";

export class BlogContentShareEdit extends BlogContentShare {
    dynamicContent = {
        ...this.dynamicContent,
        "_root:t-on-mouseup": () => {},
    };
}

registry
    .category("website.edit_active_elements")
    .add("website_blog.blog_content_share", BlogContentShareEdit);
