import { expect, test } from "@odoo/hoot";
import { animationFrame, click, press, queryAllTexts } from "@odoo/hoot-dom";
import {
    contains,
    defineModels,
    fields,
    models,
    mockService,
    mountView,
    mountWithSearch,
    onRpc,
    patchWithCleanup,
    toggleMenuItem,
    toggleSearchBarMenu,
    webModels,
} from "@web/../tests/web_test_helpers";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { Domain } from "@web/core/domain";
import { redirect } from "@web/core/utils/urls";
import { browser } from "@web/core/browser/browser";

class MockPurchaseOrders extends models.Model {
    _name = "mock.purchase.order";
    state = fields.Selection({
        selection: [
            ["draft", "Draft"],
            ["sent", "Sent"],
        ],
    });
    partner_id = fields.Many2one({ relation: "res.partner" });
    user_id = fields.Many2one({ relation: "res.users" });
    date_order = fields.Date();
    _records = [
        { id: 1, state: "draft" },
        { id: 2, state: "sent" },
        { id: 3, state: "sent" },
    ];
}

const { ResCompany, ResPartner, ResUsers } = webModels;
defineModels({ MockPurchaseOrders, ResCompany, ResPartner, ResUsers });

test("URL with single filter creates filter with domain", async () => {
    redirect("?domain=" + encodeURIComponent('[["state", "=", "sent"]]'));
    const searchBar = await mountWithSearch(SearchBar, { resModel: "mock.purchase.order" });

    expect(`.o_searchview .o_searchview_facet`).toHaveCount(1);
    expect(searchBar.env.searchModel.domain).toEqual([["state", "=", "sent"]]);
    const shared = searchBar.env.searchModel.getSearchItems(
        (it) => it.isActive && it.description === "Shared"
    )[0];
    expect(new Domain(shared.domain).toList()).toEqual([["state", "=", "sent"]]);

    // Removing the "Shared" filter should reset domain
    await contains(".o_facet_remove").click();
    expect(searchBar.env.searchModel.domain).toEqual([]);
});

test("URL with multiple filters creates shared filter", async () => {
    const domain = '["&", ["state", "=", "sent"], ["partner_id", "ilike", "me"]]';
    redirect("?domain=" + encodeURIComponent(domain));
    const searchBar = await mountWithSearch(SearchBar, { resModel: "mock.purchase.order" });
    expect(`.o_searchview .o_searchview_facet`).toHaveCount(1); // Only show 1 "shared filter"
    expect(searchBar.env.searchModel.domain).toEqual([
        "&",
        ["state", "=", "sent"],
        ["partner_id", "ilike", "me"],
    ]);
    // Also check that the search item has the correct domain (so user can edit it by clicking on it)
    const shared = searchBar.env.searchModel.getSearchItems(
        (it) => it.isActive && it.description === "Shared"
    )[0];
    expect(new Domain(shared.domain).toString()).toEqual(domain);
});

test("URL with single existing groupBy activates it", async () => {
    redirect("?groupBy=" + encodeURIComponent('["partner_id"]'));
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "mock.purchase.order",
        searchMenuTypes: ["groupBy"],
        searchViewId: false,
    });
    expect(`.o_searchview .o_searchview_facet`).toHaveCount(1);
    expect(searchBar.env.searchModel.groupBy).toEqual(["partner_id"]);
});

test("URL with multiple groupBy (incl. custom), creates and activates single groupBy", async () => {
    redirect("?groupBy=" + encodeURIComponent('["state", "partner_id"]'));
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "mock.purchase.order",
        searchMenuTypes: ["groupBy"],
        searchViewId: false,
    });
    expect(`.o_searchview .o_searchview_facet`).toHaveCount(1);
    expect(searchBar.env.searchModel.groupBy).toEqual(["state", "partner_id"]);
    const activeState = searchBar.env.searchModel.getSearchItems(
        (it) => it.isActive && it.description === "State" // New filter for custom groupBy
    );
    expect(activeState).toHaveLength(1);
});

test("URL groupBy with sub-items activated", async () => {
    redirect("?groupBy=" + encodeURIComponent('["date_order:year"]'));
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "mock.purchase.order",
        searchMenuTypes: ["groupBy"],
        searchViewId: false,
    });
    expect(searchBar.env.searchModel.groupBy).toEqual(["date_order:year"]);
});

test("URL with groupBy and orderBy activates ordered groupBy", async () => {
    const encodedgroupBy = encodeURIComponent('["partner_id"]');
    const encodedorderBy = encodeURIComponent('[{"name":"__count", "asc": false}]');
    redirect("?groupBy=" + encodedgroupBy + "&orderBy=" + encodedorderBy);
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "mock.purchase.order",
        searchMenuTypes: ["groupBy"],
        searchViewId: false,
    });
    expect(`.o_searchview .o_searchview_facet`).toHaveCount(1);
    expect(`.fa-sort-numeric-desc`).toHaveCount(1); // OrderBy desc icon
    expect(searchBar.env.searchModel.groupBy).toEqual(["partner_id"]);
    expect(searchBar.env.searchModel.orderBy).toEqual([{ asc: false, name: "__count" }]);
});

test("URL with filter + groupBy + orderBy activates filters", async () => {
    const domain = encodeURIComponent('[["state", "=", "sent"]]');
    const groupBy = encodeURIComponent('["partner_id"]');
    const orderBy = encodeURIComponent('[{"name":"__count","asc":true}]');
    const url = "?domain=" + domain + "&groupBy=" + groupBy + "&orderBy=" + orderBy;
    redirect(url);

    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "mock.purchase.order",
        searchMenuTypes: ["groupBy"],
        searchViewId: false,
    });
    expect(`.o_searchview .o_searchview_facet`).toHaveCount(2); // One for the shared filter and one for the groupby
    expect(searchBar.env.searchModel.domain).toEqual([["state", "=", "sent"]]);
    expect(searchBar.env.searchModel.groupBy).toEqual(["partner_id"]);
    expect(`.fa-sort-numeric-asc`).toHaveCount(1); // OrderBy ascending icon
    expect(searchBar.env.searchModel.orderBy).toEqual([{ asc: true, name: "__count" }]);

    // Regenerating the url should give the same result as before, without the "?"
    expect(searchBar.env.searchModel.generateQueryString()).toEqual(url.slice(1));
});

test("Bad URL with 1 faulty part still gets applied", async () => {
    mockService("notification", {
        add: (message, options) => {
            expect(message).toBe("Warning: Not all shared filters applied");
            expect(options).toEqual({ type: "warning" });
            expect.step("Partial error notification");
        },
    });

    const domain = encodeURIComponent('[["state", "=", "sent"]]');
    const groupBy = encodeURIComponent('["partner_id"]');
    const orderBy = encodeURIComponent('[{"name":"__count","as'); // Simulate faulty dict due to copy error
    const url = "?domain=" + domain + "&groupBy=" + groupBy + "&orderBy=" + orderBy;
    redirect(url);

    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "mock.purchase.order",
        searchMenuTypes: ["groupBy"],
        searchViewId: false,
    });
    expect(`.o_searchview .o_searchview_facet`).toHaveCount(2); // One for the shared filter and one for the groupby
    expect(searchBar.env.searchModel.domain).toEqual([["state", "=", "sent"]]);
    expect(searchBar.env.searchModel.groupBy).toEqual(["partner_id"]);

    expect.verifySteps(["Partial error notification"]);
});

test("Bad URL reverts to default filters", async () => {
    mockService("notification", {
        add: (message, options) => {
            expect(message).toBe("Shared filters couldn't be applied");
            expect(options).toEqual({ type: "danger" });
            expect.step("Error notification");
        },
    });

    redirect("?domain=" + encodeURIComponent('[["state", "=",]]'));

    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "mock.purchase.order",
        searchMenuTypes: ["filter", "groupBy"],
        searchViewId: false,
        searchViewArch: `
            <search>
                <filter string="Foo" name="foo" domain="[('state','=','draft')]"/>
            </search>
        `,
        context: { search_default_foo: 1 },
    });

    expect(`.o_searchview .o_searchview_facet`).toHaveCount(1); // Uses the default filter;
    expect(searchBar.env.searchModel.domain).toEqual([["state", "=", "draft"]]);

    expect.verifySteps(["Error notification"]);
});

test("Good URL does not apply default filters", async () => {
    redirect("?domain=" + encodeURIComponent('[["state", "=", "sent"]]'));

    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "mock.purchase.order",
        searchViewId: false,
        searchViewArch: `
            <search>
                <filter string="Foo" name="foo" domain="[('state','=','draft')]"/>
            </search>
        `,
        context: { search_default_foo: 1 },
    });

    expect(`.o_searchview .o_searchview_facet`).toHaveCount(1); // Only the shared filter;

    // Ensure domain does NOT include the default filter's domain
    expect(searchBar.env.searchModel.domain).toEqual([["state", "=", "sent"]]);
});

test.tags("desktop"); // mountView hides search Bar on mobile (but not mountWithSearch)
test("URL with single filter triggers RPC and filters record list", async () => {
    const encodedDomain = encodeURIComponent('[["state", "=", "sent"]]');
    redirect("?domain=" + encodedDomain);
    // In this test we focus on the RPC which is triggered by mounting a view list
    let expectedDomain = [["state", "=", "sent"]];
    onRpc(async (params) => {
        if (params.method == "web_search_read") {
            expect.step("web_search_read");
            expect(params.kwargs.domain).toEqual(expectedDomain);
        }
    });
    await mountView({
        type: "list",
        resModel: "mock.purchase.order",
        arch: `<list> <field name="state"/> </list>`,
    });

    expect(`.o_searchview .o_searchview_facet`).toHaveCount(1);
    expect(`.o_list_table .o_data_cell`).toHaveCount(2);

    // Removing the "Shared" filter should reset domain
    expectedDomain = [];
    await contains(".o_facet_remove").click();
    expect(`.o_list_table .o_data_cell`).toHaveCount(3);
    expect.verifySteps(["web_search_read", "web_search_read"]);
});

test.tags("desktop"); // Shortcut testing only on computer
test("hotkey sharing disabled on dynamic views", async () => {
    // We don't want to allow sharing filters for dynamic views, as
    // we redirect to the stored action anyways,
    await mountView({
        type: "list",
        resModel: "mock.purchase.order",
        arch: `<list> <field name="state"/> </list>`,
        // no actionId --> we interpret this as a dynamic view
    });
    await press(["control", "k"]);
    await animationFrame();
    const hotkeys = queryAllTexts(`.o_command_hotkey`);
    expect(hotkeys.some((key) => key.includes("Share \n ALT + SHIFT + H"))).toBe(false);
});

test.tags("desktop"); // Shortcut testing only on computer
test("hotkey sharing available on stored actions", async () => {
    await mountView({
        type: "list",
        resModel: "mock.purchase.order",
        arch: `<list> <field name="state"/> </list>`,
        config: { actionId: 1 }, // Just to let the search model know this is a stored action
    });

    await press(["control", "k"]);
    await animationFrame();
    const hotkeys = queryAllTexts(`.o_command_hotkey`);
    expect(hotkeys.some((key) => key.includes("Share \n ALT + SHIFT + H"))).toBe(false);
});

test.tags("desktop"); // Shortcut testing only on computer
test("hotkey sharing triggers notification", async () => {
    mockService("notification", {
        add: (message, options) => {
            expect(message).toBe("Link copied to clipboard");
            expect(options).toEqual({ type: "success" });
            expect.step("Success notification");
        },
    });

    patchWithCleanup(browser.navigator.clipboard, {
        async writeText() {
            expect.step("Copy to clipboard");
        },
    });

    await mountView({
        type: "list",
        resModel: "mock.purchase.order",
        arch: `<list> <field name="state"/> </list>`,
        config: { actionId: 1 }, // Just to let the search model know this is a stored action
    });

    await press(["alt", "shift", "h"]);
    await animationFrame();
    expect.verifySteps(["Copy to clipboard", "Success notification"]);
});

test.tags("desktop"); // Shortcut testing only on computer
test("hotkey sharing copies simple domain + groupBy to clipboard", async () => {
    // Less comprehensinve testing then decoding url, as we use the same helper
    // as when saving favorite filters to encode the search params in the url
    patchWithCleanup(browser.navigator.clipboard, {
        async writeText(url) {
            expect.step(url.split("&domain=")[1]);
        },
    });

    await mountView({
        type: "list",
        resModel: "mock.purchase.order",
        arch: `<list><field name="state"/></list>`,
        searchMenuTypes: ["filter", "groupBy"],
        searchViewArch: `
            <search>
                <filter string="Draft" name="draft" domain="[('state', '=', 'draft')]"/>
                <group expand="0" string="Group By">
                    <filter string="State" name="groupby_state" context="{'group_by': 'state'}"/>
                </group>
            </search>
        `,
        config: { actionId: 1 },
    });

    await toggleSearchBarMenu();
    await toggleMenuItem("draft");
    await toggleMenuItem("state");

    await press(["alt", "shift", "h"]);
    await animationFrame();

    expect.verifySteps([
        encodeURIComponent('[("state", "=", "draft")]') +
            "&groupBy=" +
            encodeURIComponent('["state"]'),
    ]);
});

test.tags("desktop"); // Shortcut testing only on computer
test("hotkey sharing copies complex search to clipboard", async () => {
    // Less comprehensinve testing then decoding url, as we use the same helper
    // as when saving favorite filters to encode the search params in the url
    patchWithCleanup(browser.navigator.clipboard, {
        async writeText(url) {
            expect.step(url.split("&domain=")[1]);
        },
    });

    await mountView({
        type: "list",
        resModel: "mock.purchase.order",
        arch: `<list><field name="state"/><field name="partner_id"/></list>`,
        searchMenuTypes: ["filter", "groupBy"],
        searchViewArch: `
            <search>
                <filter string="Draft" name="draft" domain="[('state', '=', 'draft')]"/>
                <filter string="Cool Vendors" name="cool_vendors" domain="[('partner_id', 'ilike', '%Juan%')]"/>
                <group expand="0" string="Group By">
                    <filter string="Vendor" name="groupby_partner_id" context="{'group_by': 'partner_id'}"/>
                </group>
            </search>
        `,
        config: { actionId: 1 },
    });

    await toggleSearchBarMenu();
    await toggleMenuItem("draft");
    await toggleMenuItem("Cool Vendors");
    await toggleMenuItem("Vendor");

    await click(".o_searchview .oi-group"); // Facet click to trigger orderBy
    await animationFrame();

    await press(["alt", "shift", "h"]);
    await animationFrame();

    expect.verifySteps([
        encodeURIComponent(`["|", ("state", "=", "draft"), ("partner_id", "ilike", "%Juan%")]`) +
            "&groupBy=" +
            encodeURIComponent('["partner_id"]') +
            "&orderBy=" +
            encodeURIComponent('[{"name":"__count","asc":false}]'),
    ]);
});
