import {
    DYNAMIC_SNIPPET,
    setDatasetIfUndefined,
} from "@website/builder/plugins/options/dynamic_snippet_option_plugin";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { DynamicSnippetBlogPostsOption } from "./dynamic_snippet_blog_posts_option";

class DynamicSnippetBlogPostsOptionPlugin extends Plugin {
    static id = "dynamicSnippetBlogPostsOption";
    static dependencies = ["dynamicSnippetOption"];
    modelNameFilter = "blog.post";
    selector = ".s_dynamic_snippet_blog_posts";
    resources = {
        builder_options: withSequence(DYNAMIC_SNIPPET, {
            OptionComponent: DynamicSnippetBlogPostsOption,
            props: {
                modelNameFilter: this.modelNameFilter,
                fetchBlogs: this.fetchBlogs.bind(this),
                fetchTags: this.fetchTags.bind(this),
                fetchAuthors: this._fetchAuthors.bind(this),
            },
            selector: this.selector,
        }),
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };
    setup() {
        this.data = {
            blogs : [],
            tags : [],
            authors : [],
        };
    }
    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(this.selector)) {
            setDatasetIfUndefined(snippetEl, "filterByBlogId", -1);
            setDatasetIfUndefined(snippetEl, "filterByTagId", -1);
            setDatasetIfUndefined(snippetEl, "filterByAuthorId", -1);
            await this.dependencies.dynamicSnippetOption.setOptionsDefaultValues(
                snippetEl,
                this.modelNameFilter
            );
        }
    }

    async fetchBlogs() {
        if (!this.data.blogs.length) {
            this.data.blogs = this._fetchData("blog.blog");
        }
        return this.data.blogs;
    }

    async fetchTags() {
        if (!this.data.tags.length) {
            this.data.tags = this._fetchData("blog.tag", []);
        }

        return this.data.tags;
    }

    async _fetchData(model, websiteDomain = []) {
        if (!websiteDomain) {
            websiteDomain = [
                "|",
                ["website_id", "=", false],
                ["website_id", "=", this.services.website.currentWebsite.id],
            ];
        }

        return this.services.orm.searchRead(model, websiteDomain, [
            "id",
            "name",
        ]);
    }

    async _fetchAuthors() {
        if (this.data.authors.length) {
            return this.data.authors;
        }

        const websiteDomain = [
            "|",
            ["website_id", "=", false],
            ["website_id", "=", this.services.website.currentWebsite.id],
        ];

        const rawGroups = await this.services.orm.call(
            "blog.post",
            "read_group",
            [websiteDomain, ["author_id"], ["author_id"]]
        );

        this.data.authors = rawGroups
            .map((group) => group.author_id)
            .filter(Boolean)
            .map(([id, name]) => ({ id, name }));

        return this.data.authors;
    }
}

registry
    .category("website-plugins")
    .add(DynamicSnippetBlogPostsOptionPlugin.id, DynamicSnippetBlogPostsOptionPlugin);
