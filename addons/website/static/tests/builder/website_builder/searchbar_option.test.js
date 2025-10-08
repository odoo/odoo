import { after, beforeEach, expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

const searchbarHTML = (orderBy) => `
    <form method="get" data-snippet="s_searchbar_input" class="o_searchbar_form s_searchbar_input" action="/pages" data-name="Search">
            <div role="search" class="input-group ">
                <input type="search" name="search" class="search-query form-control oe_search_box" placeholder="Search..." data-limit="5" data-order-by="${orderBy}" autocomplete="off" data-search-type="pages" data-display-description="true">
                <button type="submit" aria-label="Search" title="Search" class="btn oe_search_button btn-primary">
                    <i class="oi oi-search" contenteditable="false"></i>
                </button>
            </div>
        <input name="order" type="hidden" class="o_search_order_by" value="${orderBy}">
    </form>
    `;

class SearchbarTestPlugin extends Plugin {
    static id = "searchbarTestPlugin";
    resources = {
        searchbar_option_order_by_items: [
            {
                label: "Date (old to recent)",
                orderBy: "write_date asc",
                id: "write_date_asc_opt",
                dependency: "search_pages_opt",
            },
            {
                label: "something",
                orderBy: "something asc",
                id: "something_opt",
            },
        ],
    };
}

beforeEach(() => {
    registry.category("website-plugins").add(SearchbarTestPlugin.id, SearchbarTestPlugin);
    after(() => {
        registry.category("website-plugins").remove(SearchbarTestPlugin);
    });
});

test("Available 'order by' options are updated after switching search type", async () => {
    await setupWebsiteBuilder(searchbarHTML("name asc"));
    await contains(":iframe .search-query").click();
    expect("[data-label='Search within'] button.o-dropdown").toHaveText("Pages");
    await contains("[data-label='Order by'] button.o-dropdown").click();
    expect(".o_popover[role=menu] [data-action-id='setOrderBy']").toHaveCount(3);
    await contains("[data-label='Search within'] button.o-dropdown").click();
    await click(".o_popover[role=menu] [data-action-value='/website/search']");
    await contains("[data-label='Order by'] button.o-dropdown").click();
    expect(".o_popover[role=menu] [data-action-id='setOrderBy']").toHaveCount(2);
});

test("Switching search type changes data checkboxes", async () => {
    await setupWebsiteBuilder(searchbarHTML("name asc"));
    await contains(":iframe .search-query").click();
    expect("[data-label='Search within'] button.o-dropdown").toHaveText("Pages");
    expect(".form-check-input").toHaveCount(1);
    await contains("[data-label='Search within'] button.o-dropdown").click();
    await contains(".o_popover[role=menu] [data-action-value='/website/search']").click();
    expect("[data-label='Search within'] button.o-dropdown").toHaveText("Everything");
    expect(".form-check-input").toHaveCount(4);
});

test("Switching search type resets 'order by' option to default", async () => {
    await setupWebsiteBuilder(searchbarHTML("write_date asc"));
    await contains(":iframe .search-query").click();
    expect("[data-label='Search within'] button.o-dropdown").toHaveText("Pages");
    expect("[data-label='Order by'] button.o-dropdown").toHaveText("Date (old to recent)");
    await contains("[data-label='Search within'] button.o-dropdown").click();
    await contains(".o_popover[role=menu] [data-action-value='/website/search']").click();
    expect("[data-label='Search within'] button.o-dropdown").toHaveText("Everything");
    expect("[data-label='Order by'] button.o-dropdown").toHaveText("Name (A-Z)");
});

test("Switching search type keeps 'order by' option if it exists on both types", async () => {
    await setupWebsiteBuilder(searchbarHTML("something asc"));
    await contains(":iframe .search-query").click();
    expect("[data-label='Search within'] button.o-dropdown").toHaveText("Pages");
    expect("[data-label='Order by'] button.o-dropdown").toHaveText("something");
    await contains("[data-label='Search within'] button.o-dropdown").click();
    await contains(".o_popover[role=menu] [data-action-value='/website/search']").click();
    expect("[data-label='Search within'] button.o-dropdown").toHaveText("Everything");
    expect("[data-label='Order by'] button.o-dropdown").toHaveText("something");
});

test("Search query's parent is not contenteditable", async () => {
    await setupWebsiteBuilder(searchbarHTML("name asc"));

    expect(":iframe .s_searchbar_input .search-query").toHaveAttribute("contenteditable", "false");
    expect(":iframe .s_searchbar_input :has(:scope > .search-query)").toHaveAttribute(
        "contenteditable",
        "false"
    );

    expect(
        ":iframe .s_searchbar_input :has(:scope > .search-query) > *:not(.search-query)"
    ).toHaveAttribute("contenteditable", "true");
});

test("Multiple searchbars parents are disabled", async () => {
    await setupWebsiteBuilder(`
        ${searchbarHTML("name asc")}
        ${searchbarHTML("date desc")}
    `);

    expect(":iframe .s_searchbar_input .search-query").toHaveCount(2);
    expect(":iframe .s_searchbar_input .search-query").toHaveAttribute("contenteditable", "false");

    expect(":iframe .s_searchbar_input :has(:scope > .search-query)").toHaveAttribute(
        "contenteditable",
        "false"
    );
});
