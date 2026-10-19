import { registry } from "@web/core/registry";
import { DynamicSnippetCarousel } from "@website/snippets/s_dynamic_snippet_carousel/dynamic_snippet_carousel";
import { BlogPostsMixin } from "./blog_posts_mixin";

const BlogPostsCarouselBase = BlogPostsMixin(DynamicSnippetCarousel);

export class BlogPostsCarousel extends BlogPostsCarouselBase {
    static selector = ".s_blog_posts_carousel";
}

registry.category("public.interactions.edit").add("website_blog.blog_posts_carousel_base", {
    Interaction: BlogPostsCarouselBase,
    isAbstract: true,
});

registry.category("public.interactions").add("website_blog.blog_posts_carousel", BlogPostsCarousel);

registry.category("public.interactions.edit").add("website_blog.blog_posts_carousel", {
    Interaction: BlogPostsCarousel,
});
