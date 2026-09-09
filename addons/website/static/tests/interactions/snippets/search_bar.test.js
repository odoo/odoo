import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

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
                <span class="oe_search_found">
                    <small></small>
                </span>
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
        expect(json.params.options.displayImage).toBe("false");
        expect(json.params.options.displayDescription).toBe("false");
        expect(json.params.options.displayExtraLink).toBe("true");
        expect(json.params.options.displayDetail).toBe("false");
        return {
            "results": [
                {
                    "_fa": "fa-file-o",
                    "name": "Xyz 1",
                    "website_url": "/website/test/xyz-1",
                },
                {
                    "_fa": "fa-file-o",
                    "name": "Xyz 2",
                    "website_url": "/website/test/xyz-2",
                },
                {
                    "_fa": "fa-file-o",
                    "name": "Xyz 3",
                    "website_url": "/website/test/xyz-3",
                }
            ],
            "results_count": 3,
            "parts": {
                "name": true,
                "website_url": true,
            },
            "fuzzy_search": false
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
    const resultEls = queryAll("form a:has(.o_search_result_item)");
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
    const resultEls = queryAll("form a:has(.o_search_result_item)");
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
    expect(queryAll("form a:has(.o_search_result_item)")).toHaveLength(3);
    await press("escape");
    expect(queryAll("form a:has(.o_search_result_item)")).toHaveLength(0);
});

test("search count span is updated with search result count", async () => {
    let searchCount = 0;
    function supportAutocomplete() {
        onRpc("/website/snippet/autocomplete", async (args) => {
            searchCount++;
            const json = JSON.parse(new TextDecoder().decode(await args.arrayBuffer()));
            expect(json.params.search_type).toBe("test");
            if (searchCount === 1) {
                expect(json.params.term).toBe("xy");
            } else if (searchCount === 2) {
                expect(json.params.term).toBe("xyz");
            }
            expect(json.params.order).toBe("test desc");
            expect(json.params.limit).toBe(3);
            expect(json.params.options.displayImage).toBe("false");
            expect(json.params.options.displayDescription).toBe("false");
            expect(json.params.options.displayExtraLink).toBe("true");
            expect(json.params.options.displayDetail).toBe("false");
            const results = {
                results: [
                    {
                        _fa: "fa-file-o",
                        name: "Xy 1",
                        website_url: "/website/test/xy1",
                    },
                    {
                        _fa: "fa-file-o",
                        name: "Xy 2",
                        website_url: "/website/test/xy-2",
                    },
                ],
                results_count: 2,
                parts: {
                    name: true,
                    website_url: true,
                },
                fuzzy_search: false,
            };

            if (searchCount === 2) {
                results["results"] = [
                    {
                        _fa: "fa-file-o",
                        name: "Xyz 3",
                        website_url: "/website/test/xyz-3",
                    },
                ];
                results["results_count"] = 1;
            }
            return results;
        });
    }

    supportAutocomplete();
    const { core } = await startInteractions(searchTemplate);
    expect(core.interactions).toHaveLength(1);
    expect(queryAll("form .o_search_result_item")).toHaveLength(0);
    expect(queryOne("form .oe_search_found small")).toHaveText("");
    await click("form input[type=search]");
    await press("x");
    await advanceTime(200);
    await press("y");
    await advanceTime(400);
    expect(queryAll("form .o_search_result_item")).toHaveLength(2);
    expect(queryOne("form .oe_search_found small")).toHaveText("(2 found)");
    await press("z");
    await advanceTime(400);
    expect(queryAll("form .o_search_result_item")).toHaveLength(1);
    expect(queryOne("form .oe_search_found small")).toHaveText("(1 found)");
});
