import { onWillStart, useState } from "@odoo/owl";
import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { useDynamicSnippetOption } from "@website/builder/plugins/options/dynamic_snippet_hook";

export class DynamicSnippetBlogPostsOption extends BaseOptionComponent {
    static template = "website_blog.DynamicSnippetBlogPostsOption";
    static dependencies = ["dynamicSnippetBlogPostsOption", "history"];
    static selector = ".s_dynamic_snippet_blog_posts";
    static components = { SelectMenu };
    setup() {
        super.setup();
        const { fetchAuthors, getModelNameFilter } = this.dependencies.dynamicSnippetBlogPostsOption;
        this.modelNameFilter = getModelNameFilter();
        this.dynamicOptionParams = useDynamicSnippetOption(this.modelNameFilter);
        this.blogState = useState({
            authors: [],
            value: [],
        });
        onWillStart(async () => {
            this.blogState.authors.push(...(await fetchAuthors(this.env.getEditingElement())));
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
    showCoverImageOption() {
        return [
            "website_blog.dynamic_filter_template_blog_post_single_aside",
            "website_blog.dynamic_filter_template_blog_post_single_circle",
        ].includes(this.templateKeyState.templateKey);
    }
    onSelect(item) {
        this.blogState.value = item;
        const el = this.env.getEditingElement();
        el.dataset.filterByAuthorIds = JSON.stringify(item);
        this.dependencies.history.addStep();
    }
}
