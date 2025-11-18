import { onWillStart, useState } from "@odoo/owl";
import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { useDynamicSnippetOption } from "@website/builder/plugins/options/dynamic_snippet_hook";

export class DynamicSnippetBlogPostsOption extends BaseOptionComponent {
    static template = "website_blog.DynamicSnippetBlogPostsOption";
    static dependencies = ["dynamicSnippetBlogPostsOption"];
    static selector = ".s_dynamic_snippet_blog_posts, .s_blog_posts_carousel";
    setup() {
        super.setup();
        const { fetchBlogs, getModelNameFilter } = this.dependencies.dynamicSnippetBlogPostsOption;
        this.modelNameFilter = getModelNameFilter();
        this.dynamicOptionParams = useDynamicSnippetOption(this.modelNameFilter);
        this.blogState = useState({
            blogs: [],
        });
        onWillStart(async () => {
            this.blogState.blogs.push(...(await fetchBlogs()));
        });
        this.domState = useDomState((el) => ({
            templateKey: el.dataset.templateKey,
            isCarousel: el.classList.contains("s_blog_posts_carousel"),
        }));
    }
    showPictureSizeOption() {
        return [
            "website_blog.dynamic_filter_template_blog_post_big_picture",
            "website_blog.dynamic_filter_template_blog_post_horizontal",
            "website_blog.dynamic_filter_template_blog_post_card",
        ].includes(this.domState.templateKey);
    }
    showTeaserOption() {
        return [
            "website_blog.dynamic_filter_template_blog_post_list",
            "website_blog.dynamic_filter_template_blog_post_card",
        ].includes(this.domState.templateKey);
    }
    showDateOption() {
        return [
            "website_blog.dynamic_filter_template_blog_post_list",
            "website_blog.dynamic_filter_template_blog_post_horizontal",
            "website_blog.dynamic_filter_template_blog_post_card",
            "website_blog.dynamic_filter_template_blog_post_single_full",
            "website_blog.dynamic_filter_template_blog_post_single_aside",
            "website_blog.dynamic_filter_template_blog_post_single_circle",
        ].includes(this.domState.templateKey);
    }
    showCategoryOption() {
        return [
            "website_blog.dynamic_filter_template_blog_post_list",
            "website_blog.dynamic_filter_template_blog_post_horizontal",
            "website_blog.dynamic_filter_template_blog_post_card",
            "website_blog.dynamic_filter_template_blog_post_single_full",
            "website_blog.dynamic_filter_template_blog_post_single_aside",
            "website_blog.dynamic_filter_template_blog_post_single_circle",
            "website_blog.dynamic_filter_template_blog_post_single_badge",
        ].includes(this.domState.templateKey);
    }
    showNewTagOption() {
        return (
            this.domState.templateKey ===
            "website_blog.dynamic_filter_template_blog_post_single_badge"
        );
    }
    showHoverEffectOption() {
        return (
            this.domState.templateKey ===
            "website_blog.dynamic_filter_template_blog_post_big_picture"
        );
    }
}
