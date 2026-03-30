import { expect, queryOne, test } from "@odoo/hoot";
import { SelectMany2X } from "@html_builder/core/building_blocks/select_many2x";
import { contains, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
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
            })
    );
    onRpc(
        "/website/snippet/filter_templates",
        async (args) =>
            new Promise((resolve) => {
                resolve([]);
            })
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
                case "res.partner":
                    this.state.searchResults = [
                        {
                            id: 1,
                            display_name: "Author 1",
                            name: "Author 1",
                        },
                    ];
                    break;
            }
        },
    });

    await setupWebsiteBuilderWithSnippet(["s_blog_posts"]);
    await contains(":iframe .s_blog_posts").click();

    const readSearchInfo = () => {
        const sharedSnippetEl = queryOne(":iframe .s_blog_posts [data-oe-shared-snippet]");
        const searchDomainInfo = sharedSnippetEl.dataset.searchDomainInfo;
        return searchDomainInfo ? JSON.parse(searchDomainInfo) : {};
    };

    // Check for blog filter
    expect(readSearchInfo()).not.toInclude("blogByIds");
    await contains("[data-label=Blogs] button.dropdown").click();
    await contains(".dropdown-item:contains(Test Blog 1)").click();
    expect(readSearchInfo()).toInclude([
        "blogByIds",
        [{ id: 1, display_name: "Test Blog 1", name: "Test Blog 1" }],
    ]);

    // Check for tag filter
    expect(readSearchInfo()).not.toInclude("blogByTagIds");
    await contains("[data-label=Tags] button.dropdown").click();
    await contains(".dropdown-item:contains(Adventure)").click();
    expect(readSearchInfo()).toInclude([
        "blogByTagIds",
        [{ id: 1, display_name: "Adventure", name: "Adventure" }],
    ]);

    // Check for author filter
    expect(readSearchInfo()).not.toInclude("blogByAuthorIds");
    await contains("div[data-label=Authors] .dropdown").click();
    await contains(".dropdown-item:contains(Author 1)").click();
    expect(readSearchInfo()).toInclude([
        "blogByAuthorIds",
        [{ id: 1, display_name: "Author 1", name: "Author 1" }],
    ]);

    // Check the constructed filter
    expect(":iframe .s_blog_posts [data-oe-shared-snippet]").toHaveAttribute(
        "data-arg-search_domain",
        `[["blog_id","in",[1]],["tag_ids","in",[1]],["author_id","in",[1]]]`
    );
});
