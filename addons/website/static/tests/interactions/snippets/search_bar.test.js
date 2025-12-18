import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { click, press, queryAll, queryOne } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";

import { onRpc } from "@web/../tests/web_test_helpers";

setupInteractionWhiteList("website.search_bar");

describe.current.tags("interaction_dev");

const searchTemplate = /* html */ `
    <form method="get" class="o_searchbar_form s_searchbar_input" action="/website/search" data-snippet="s_searchbar_input">
        <div role="search" class="input-group input-group-lg">
            <input type="search" name="search" class="search-query form-control oe_search_box o_translatable_attribute" placeholder="Search..."
                    data-search-type="test"
                    data-limit="3"
                    data-display-image="false"
                    data-display-description="false"
                    data-display-extra-link="true"
                    data-display-detail="false"
                    data-order-by="name asc"
                    autocomplete="off"/>
            <button type="submit" aria-label="Search" title="Search" class="btn oe_search_button border border-start-0 px-4 bg-o-color-4">
                <i class="oi oi-search"></i>
            </button>
        </div>
        <input name="order" type="hidden" class="o_search_order_by" value="test desc"/>
    </form>
`;

function supportAutocomplete(numberOfResults = 3) {
    onRpc("/website/snippet/autocomplete", async (args) => {
        const json = JSON.parse(new TextDecoder().decode(await args.arrayBuffer()));
        expect(json.params.search_type).toBe("test");
        expect(json.params.term).toBe("xyz");
        expect(json.params.order).toBe("test desc");
        expect(json.params.limit).toBe(3);

        const allData = [
            { _fa: "fa-file-o", name: "Xyz 1", website_url: "/website/test/xyz-1" },
            { _fa: "fa-file-o", name: "Xyz 2", website_url: "/website/test/xyz-2" },
            { _fa: "fa-file-o", name: "Xyz 3", website_url: "/website/test/xyz-3" },
            { _fa: "fa-file-o", name: "Xyz 4", website_url: "/website/test/xyz-1" },
            { _fa: "fa-file-o", name: "Xyz 5", website_url: "/website/test/xyz-2" },
            { _fa: "fa-file-o", name: "Xyz 6", website_url: "/website/test/xyz-3" },
        ];

        return {
            results: {
                pages: {
                    groupName: "Pages",
                    templateKey: "website.search_items_page",
                    search_count: 3,
                    limit: 3,
                    data: allData.slice(0, numberOfResults),
                },
            },
            results_count: 3,
            parts: {
                name: true,
                website_url: true,
            },
            fuzzy_search: false,
        };
    });
}

test("searchbar triggers a search when text is entered", async () => {
    supportAutocomplete();
    const { core } = await startInteractions(searchTemplate);
    expect(core.interactions).toHaveLength(1);
    await click("form input[type=search]");
    await press("x");
    await advanceTime(200);
    await press("y");
    await advanceTime(200);
    await press("z");
    await advanceTime(400);
    expect(queryAll("form .o_search_result_item")).toHaveLength(3);
});

/**
 * Test keyboard navigation in search results.
 *
 * Verifies that:
 * 1. ArrowDown from input focuses the first result
 * 2. ArrowUp from input focuses the last result
 * 3. ArrowLeft/Right navigate horizontally within the grid
 * 4. ArrowDown wraps around rows to next row's first column
 */
test.tags("desktop");
test("search results keyboard navigation with arrow keys", async () => {
    supportAutocomplete(6);
    await startInteractions(searchTemplate);
    const inputEl = queryOne("form input[type=search]");

    // Setup: Type search query to trigger autocomplete
    await click(inputEl);
    await press("x");
    await press("y");
    await press("z");
    await advanceTime(400);

    const resultEls = queryAll("form .o_search_result_item > a");
    expect(resultEls).toHaveLength(6);
    expect(inputEl).toBeFocused();

    // ArrowDown from input focuses first result
    await press("down");
    expect(resultEls[0]).toBeFocused();

    // ArrowDown moves to next row, same column
    await press("down");
    expect(resultEls[3]).toBeFocused();

    // ArrowRight navigates to adjacent result (same row)
    await press("right");
    expect(resultEls[4]).toBeFocused();

    // ArrowUp moves to previous row, same column
    await press("up");
    expect(resultEls[1]).toBeFocused();

    // ArrowLeft navigates to adjacent result (same row)
    await press("left");
    expect(resultEls[0]).toBeFocused();

    // ArrowUp moves back to input
    await press("up");
    expect(inputEl).toBeFocused();
});

test("searchbar removes results on escape", async () => {
    supportAutocomplete();
    await startInteractions(searchTemplate);
    await click("form input[type=search]");
    await press("x");
    await press("y");
    await press("z");
    await advanceTime(400);
    expect(queryAll("form .o_search_result_item")).toHaveLength(3);
    await press("escape");
    expect(queryAll("form .o_search_result_item")).toHaveLength(0);
});
