import { expect, test } from "@odoo/hoot";
import { SelectMany2X } from "@html_builder/core/building_blocks/select_many2x";
import {
    contains,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("dynamic Snippet Blog Filter", async () => {
    // We just need to fulfill these two RPCs, they are not useful in test.
    onRpc(
        "/website/snippet/options_filters",
        async (args) =>
            new Promise((resolve) => {
                resolve([]);
            }),
    );
    onRpc(
        "/website/snippet/filter_templates",
        async (args) =>
            new Promise((resolve) => {
                resolve([]);
            }),
    );

    // Provide blogs, tags and authors for the filters
    patchWithCleanup(SelectMany2X.prototype, {
        search() {
            switch (this.props.model) {
                case "blog.blog":
                    this.state.searchResults = [
                        {
                            id: 1,
                            display_name: "Test Blog 1",
                            name: "Test Blog 1",
                        },
                    ];
                    break;
                case "blog.tag":
                    this.state.searchResults = [
                        {
                            id: 1,
                            display_name: "Adventure",
                            name: "Adventure",
                        },
                    ];
                    break;
            }
        },
    });
    onRpc("blog.post", "formatted_read_group", () => [
        {
            author_id: [1, "Author 1"],
            __count: 1,
        },
    ]);

    await setupWebsiteBuilderWithSnippet(["s_blog_posts"]);
    await contains(":iframe .s_blog_posts").click();

    // Check for blog filter
    expect(":iframe .s_blog_posts").not.toHaveAttribute(
        "data-filter-by-blog-ids",
    );
    await contains("[data-label=Blogs] button.dropdown").click();
    await contains(".dropdown-item:contains(Test Blog 1)").click();
    expect(":iframe .s_blog_posts").toHaveAttribute(
        "data-filter-by-blog-ids",
        '[{"id":1,"display_name":"Test Blog 1","name":"Test Blog 1"}]',
    );

    // Check for tag filter
    expect(":iframe .s_blog_posts").not.toHaveAttribute(
        "data-filter-by-tag-ids",
    );
    await contains("[data-label=Tags] button.dropdown").click();
    await contains(".dropdown-item:contains(Adventure)").click();
    expect(":iframe .s_blog_posts").toHaveAttribute(
        "data-filter-by-tag-ids",
        '[{"id":1,"display_name":"Adventure","name":"Adventure"}]',
    );

    // Check for author filter
    expect(":iframe .s_blog_posts").not.toHaveAttribute(
        "data-filter-by-author-ids",
    )
    await contains("div[data-label=Authors] .dropdown").click();
    await contains(".dropdown-item:contains(Author 1)").click();
    expect(":iframe .s_blog_posts").toHaveAttribute(
        "data-filter-by-author-ids",
        '[{"id":1,"name":"Author 1"}]',
    );
});
