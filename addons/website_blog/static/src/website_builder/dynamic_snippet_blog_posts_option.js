import { onWillStart, useState } from "@odoo/owl";
import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { useDynamicSnippetOption } from "@website/builder/plugins/options/dynamic_snippet_hook";

export class DynamicSnippetBlogPostsOption extends BaseOptionComponent {
    static template = "website_blog.DynamicSnippetBlogPostsOption";
    static dependencies = ["dynamicSnippetBlogPostsOption"];
    static selector = ".s_dynamic_snippet_blog_posts";
    setup() {
        super.setup();
        const { fetchBlogs, getModelNameFilter } = this.dependencies.dynamicSnippetBlogPostsOption;
        this.dynamicOptionParams = useDynamicSnippetOption(getModelNameFilter());
        this.blogState = useState({
            blogs: [],
        });
        onWillStart(async () => {
            this.blogState.blogs.push(...(await fetchBlogs()));
        });
        this.templateKeyState = useDomState((el) => ({
            templateKey: el.dataset.templateKey,
        }));
    }
    showPictureSizeOption() {
        return [
            "website_blog.dynamic_filter_template_blog_post_big_picture",
            "website_blog.dynamic_filter_template_blog_post_horizontal",
            "website_blog.dynamic_filter_template_blog_post_card",
        ].includes(this.templateKeyState.templateKey);
    }
    showTeaserOption() {
        return [
            "website_blog.dynamic_filter_template_blog_post_list",
            "website_blog.dynamic_filter_template_blog_post_card",
        ].includes(this.templateKeyState.templateKey);
    }
    showDateOption() {
        return [
            "website_blog.dynamic_filter_template_blog_post_list",
            "website_blog.dynamic_filter_template_blog_post_horizontal",
            "website_blog.dynamic_filter_template_blog_post_card",
            "website_blog.dynamic_filter_template_blog_post_single_full",
            "website_blog.dynamic_filter_template_blog_post_single_aside",
            "website_blog.dynamic_filter_template_blog_post_single_circle",
        ].includes(this.templateKeyState.templateKey);
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
        ].includes(this.templateKeyState.templateKey);
    }
    showNewTagOption() {
        return (
            this.templateKeyState.templateKey ===
            "website_blog.dynamic_filter_template_blog_post_single_badge"
        );
    }
    showHoverEffectOption() {
        return (
            this.templateKeyState.templateKey ===
            "website_blog.dynamic_filter_template_blog_post_big_picture"
        );
    }
    showCoverImage() {
        return (
            this.templateKeyState.templateKey ===
            "website_blog.dynamic_filter_template_blog_post_single_aside"
        );
    }
}
