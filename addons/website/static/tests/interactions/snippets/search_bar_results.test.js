import { describe, expect, test } from "@odoo/hoot";
import { press, queryAll, queryOne } from "@odoo/hoot-dom";
import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";

setupInteractionWhiteList("website.search_bar_results");
describe.current.tags("interaction_dev");

const searchTemplate = `
    <form method="get" class="o_searchbar_form s_searchbar_input" action="/website/search" data-snippet="s_searchbar_input">
        <div role="search" class="input-group input-group-lg">
            <input type="search" name="search" class="search-query form-control oe_search_box" placeholder="Search..."
                    data-search-type="test"
                    data-limit="3"
                    data-display-image="false"
                    data-display-description="false"
                    data-display-extra-link="true"
                    data-display-detail="false"
                    data-order-by="name asc"
                    autocomplete="off"
            />
            <button type="submit" aria-label="Search" title="Search" class="btn oe_search_button border border-start-0 px-4 bg-o-color-4">
                <i class="oi oi-search"></i>
            </button>
        </div>
        <input name="order" type="hidden" class="o_search_order_by" value="test desc"/>
        <div class="o_dropdown_menu show position-absolute dropdown">
            <a class="dropdown-item" href="/website/test/xyz-1">
                <div class="o_search_result_item">
                    Xyz 1
                </div>
            </a>
            <a class="dropdown-item" href="/website/test/xyz-2">
                <div class="o_search_result_item">
                    Xyz 2
                </div>
            </a>
        </div>
    </form>
`;

test("searchbar selects next result on cursor down", async () => {
    await startInteractions(searchTemplate);
    const resultEls = queryAll("form a:has(.o_search_result_item)");
    resultEls[0].focus();
    await press("down");
    expect(document.activeElement).toBe(resultEls[1]);
});

test("searchbar selects input on cursor down on last result", async () => {
    await startInteractions(searchTemplate);
    queryOne("form a:has(.o_search_result_item):eq(1)").focus();
    await press("down");
    expect(document.activeElement).toBe(queryOne("form input[type=search]"));
});

test("searchbar selects previous result on cursor up", async () => {
    await startInteractions(searchTemplate);
    const resultEls = queryAll("form a:has(.o_search_result_item)");
    resultEls[1].focus();
    await press("up");
    expect(document.activeElement).toBe(resultEls[0]);
});

test("searchbar selects input on cursor up on first result", async () => {
    await startInteractions(searchTemplate);
    queryOne("form a:has(.o_search_result_item):first").focus();
    await press("up");
    expect(document.activeElement).toBe(queryOne("form input[type=search]"));
});
