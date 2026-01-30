import { DynamicSnippetCarousel } from "@website/snippets/s_dynamic_snippet_carousel/dynamic_snippet_carousel";
import { registry } from "@web/core/registry";
import { BlogPostsMixin } from "./blog_posts_mixin";

export class DynamicSnippetCarouselBlogs extends BlogPostsMixin(DynamicSnippetCarousel) {
    static selector = ".s_blog_posts_carousel";

    renderContent() {
        super.renderContent();
        const rowEl = this.el.querySelectorAll(".s_dynamic_snippet_row");
        rowEl.forEach((row) => {
            row.classList.remove("s_dynamic_snippet_row");
        });
    }
}

registry
    .category("public.interactions")
    .add("website_blog.blog_posts_carousel", DynamicSnippetCarouselBlogs);

registry.category("public.interactions.edit").add("website_blog.blog_posts_carousel", {
    Interaction: DynamicSnippetCarouselBlogs,
});
