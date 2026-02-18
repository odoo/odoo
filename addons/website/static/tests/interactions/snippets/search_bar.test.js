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
                    data-order-by="name asc"
                    autocomplete="off"/>
            <button type="submit" aria-label="Search" title="Search" class="btn oe_search_button border border-start-0 px-4 bg-o-color-4">
                <i class="oi oi-search"></i>
            </button>
        </div>
        <input name="order" type="hidden" class="o_search_order_by" value="test desc"/>
    </form>
`;

function supportAutocomplete() {
    onRpc("/website/snippet/autocomplete", async (args) => {
        const json = JSON.parse(new TextDecoder().decode(await args.arrayBuffer()));
        expect(json.params.search_type).toBe("test");
        expect(json.params.term).toBe("xyz");
        expect(json.params.order).toBe("test desc");
        expect(json.params.limit).toBe(3);
        return {
            results: {
                pages: {
                    groupName: "Pages",
                    templateKey: "website.search_items_page",
                    search_count: 3,
                    limit: 3,
                    data: [
                        {
                            _fa: "fa-file-o",
                            name: "Xyz 1",
                            website_url: "/website/test/xyz-1",
                        },
                        {
                            _fa: "fa-file-o",
                            name: "Xyz 2",
                            website_url: "/website/test/xyz-2",
                        },
                        {
                            _fa: "fa-file-o",
                            name: "Xyz 3",
                            website_url: "/website/test/xyz-3",
                        },
                    ],
                },
            },
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

test("searchbar selects first result on cursor down", async () => {
    supportAutocomplete();
    await startInteractions(searchTemplate);
    const inputEl = queryOne("form input[type=search]");
    await click(inputEl);
    await press("x");
    await press("y");
    await press("z");
    await advanceTime(400);
    const resultEls = queryAll("form a.o_search_result_link");
    expect(resultEls).toHaveLength(3);
    expect(document.activeElement).toBe(inputEl);
    await press("down");
    expect(document.activeElement).toBe(resultEls[0]);
});

test("searchbar selects last result on cursor up", async () => {
    supportAutocomplete();
    await startInteractions(searchTemplate);
    const inputEl = queryOne("form input[type=search]");
    await click(inputEl);
    await press("x");
    await press("y");
    await press("z");
    await advanceTime(400);
    const resultEls = queryAll("form a.o_search_result_link");
    expect(resultEls).toHaveLength(3);
    expect(document.activeElement).toBe(inputEl);
    await press("up");
    expect(document.activeElement).toBe(resultEls[2]);
});

test("searchbar removes results on escape", async () => {
    supportAutocomplete();
    await startInteractions(searchTemplate);
    await click("form input[type=search]");
    await press("x");
    await press("y");
    await press("z");
    await advanceTime(400);
    expect(queryAll("form a.o_search_result_link")).toHaveLength(3);
    await press("escape");
    expect(queryAll("form a.o_search_result_link")).toHaveLength(0);
});
