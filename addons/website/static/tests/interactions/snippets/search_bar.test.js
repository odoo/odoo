import { setupInteractionWhiteList } from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { click, press, queryAll, queryOne } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";

import { onRpc } from "@web/../tests/web_test_helpers";
import { startInteractionsWithSnippet } from "../helpers";

setupInteractionWhiteList("website.search_bar");

describe.current.tags("interaction_dev");

function processSearchBarHTML(html) {
    const formEl = html.querySelector("[data-snippet='s_searchbar_input']");
    Object.assign(formEl.querySelector("input[type=search]").dataset, {
        searchType: "test",
        limit: 3,
        orderBy: "name asc",
    });
    formEl.querySelector(".o_search_order_by").value = "test desc";
}

function supportAutocomplete() {
    onRpc("/website/snippet/autocomplete", async (args) => {
        const json = JSON.parse(new TextDecoder().decode(await args.arrayBuffer()));
        expect(json.params.search_type).toBe("test");
        expect(json.params.term).toBe("xyz");
        expect(json.params.order).toBe("test desc");
        expect(json.params.limit).toBe(3);
        const data = [
            {
                _fa: "description",
                name: "Xyz 1",
                website_url: "/website/test/xyz-1",
            },
            {
                _fa: "description",
                name: "Xyz 2",
                website_url: "/website/test/xyz-2",
            },
            {
                _fa: "description",
                name: "Xyz 3",
                website_url: "/website/test/xyz-3",
            },
        ];
        return {
            results: data
                .map(
                    (item) =>
                        `<li class="o_search_result_item rounded">
                            <a class="o_search_result_link d-flex gap-2 p-2 text-decoration-none text-muted" href="${item.website_url}">
                                <i class="o_search_result_image flex-shrink-0 align-content-center rounded-2 fs-6 text-center text-muted fa ${item._fa}"></i>
                                <div class="o_search_result_content d-flex flex-grow-1">
                                    <div>
                                        <h3 class="h6 mb-0 d-inline">${item.name}</h3>
                                    </div>
                                    <div class="o_search_result_description d-empty-none w-100 w-md-50"></div>
                                </div>
                            </a>
                        </li>`
                )
                .join(""),
        };
    });
}

test("searchbar triggers a search when text is entered", async () => {
    supportAutocomplete();
    const { core } = await startInteractionsWithSnippet("s_searchbar_input", {
        processHTML: processSearchBarHTML,
    });
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
    await startInteractionsWithSnippet("s_searchbar_input", {
        processHTML: processSearchBarHTML,
    });
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
    await startInteractionsWithSnippet("s_searchbar_input", {
        processHTML: processSearchBarHTML,
    });
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
    await startInteractionsWithSnippet("s_searchbar_input", {
        processHTML: processSearchBarHTML,
    });
    await click("form input[type=search]");
    await press("x");
    await press("y");
    await press("z");
    await advanceTime(400);
    expect(queryAll("form a.o_search_result_link")).toHaveLength(3);
    await press("escape");
    expect(queryAll("form a.o_search_result_link")).toHaveLength(0);
});
