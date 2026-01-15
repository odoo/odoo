import { registry } from "@web/core/registry";
import { PostLink } from "@website/interactions/post_link";

// TODO: remove in master
export class BlogPostLink extends PostLink {
    static selector = "select[name='archive'], span:has(.fa-calendar-o) a";
}

registry.category("public.interactions").add("website_blog.blog_post_link", BlogPostLink);
