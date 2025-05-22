import { onWillStart, useState } from "@odoo/owl";
import { DynamicSnippetOption } from "@website/builder/plugins/options/dynamic_snippet_option";
import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { useDynamicSnippetOption } from "@website/builder/plugins/options/dynamic_snippet_hook";

export class DynamicSnippetBlogPostsOption extends BaseOptionComponent {
    static template = "website_blog.DynamicSnippetBlogPostsOption";
    static props = {
        ...DynamicSnippetOption.props,
        fetchBlogs: Function,
    };
    setup() {
        super.setup();
        this.dynamicOptionParams = useDynamicSnippetOption(this.props.modelNameFilter);
        this.blogState = useState({
            blogs: [],
        });
        onWillStart(async () => {
            this.blogState.blogs.push(...(await this.props.fetchBlogs()));
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
        ].includes(this.templateKeyState.templateKey);
    }
}
