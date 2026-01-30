import { DynamicSnippet } from "@website/snippets/s_dynamic_snippet/dynamic_snippet";
import { registry } from "@web/core/registry";
import { BlogPostsMixin } from "./blog_posts_mixin";

export class BlogPosts extends BlogPostsMixin(DynamicSnippet) {
    static selector = ".s_dynamic_snippet_blog_posts";
}

registry.category("public.interactions").add("website_blog.blog_posts", BlogPosts);

registry.category("public.interactions.edit").add("website_blog.blog_posts", {
    Interaction: BlogPosts,
});
