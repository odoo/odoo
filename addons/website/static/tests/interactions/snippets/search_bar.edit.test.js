import { queryOne, click, press } from "@odoo/hoot-dom";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";
import { switchToEditMode } from "../../helpers";
import { describe, expect, test } from "@odoo/hoot";

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
                <span class="o_total_search_count"></span>
                <i class="oi oi-search"></i>
            </button>
        </div>
        <input name="order" type="hidden" class="o_search_order_by" value="test desc"/>
    </form>
`;

test("searchbar placeholder can be customized", async () => {
    const { core } = await startInteractions(searchTemplate, {
        waitForStart: true,
        editMode: true,
    });
    await switchToEditMode(core);
    expect(core.interactions).toHaveLength(1);
    const inputEl = queryOne(".search-query");
    await click(inputEl);
    await press("x");
});

// test("searchbar placeholder can be customized", async () => {
//     await setupWebsiteBuilderWithSnippet("s_searchbar_input");
//     debugger;
// })
