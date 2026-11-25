import { beforeEach, expect, test, waitFor, fill } from "@odoo/hoot";
import { animationFrame, press, queryAllTexts, runAllTimers } from "@odoo/hoot-dom";
import {
    contains,
    defineModels,
    fields,
    getService,
    models,
    mockService,
    mountView,
    mountWithSearch,
    onRpc,
    patchWithCleanup,
    toggleMenuItem,
    toggleMenuItemOption,
    toggleSearchBarMenu,
    webModels,
    defineActions,
    getFacetTexts,
    mountWebClient,
    mountWithCleanup,
    switchView,
} from "@web/../tests/web_test_helpers";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { Domain } from "@web/core/domain";
import { parseSearchQuery } from "@web/core/browser/router";
import { pick } from "@web/core/utils/objects";
import { redirect } from "@web/core/utils/urls";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { browser, location } from "@web/core/browser/browser";
import { WebClient } from "@web/webclient/webclient";

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

const SHARE_KEY = "Share\nALT + SHIFT + H";

/**
 * Search of an URL query string, as given by the action plugin to the view of
 * the action loaded from that URL.
 */
function fromUrl(query) {
    return pick(parseSearchQuery(query), "domain", "groupBy", "orderBy");
}

const { ResCompany, ResPartner, ResUsers } = webModels;
defineModels({ MockPurchaseOrders, ResCompany, ResPartner, ResUsers });

/** URLs written to the clipboard during a test, captured by the patch below. */
let clipboardWrites;
beforeEach(() => {
    clipboardWrites = [];
    patchWithCleanup(browser.navigator.clipboard, {
        async writeText(text) {
            clipboardWrites.push(text);
        },
    });
});

test("URL with single filter creates filter with domain", async () => {
    const urlSearch = fromUrl("?domain=" + encodeURIComponent('[["state", "=", "sent"]]'));
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "mock.purchase.order",
        urlSearch,
    });

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
    const urlSearch = fromUrl("?domain=" + encodeURIComponent(domain));
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "mock.purchase.order",
        urlSearch,
    });
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
    const urlSearch = fromUrl("?groupBy=" + encodeURIComponent('["partner_id"]'));
    const searchBar = await mountWithSearch(SearchBar, {
        urlSearch,
        resModel: "mock.purchase.order",
        searchMenuTypes: ["groupBy"],
        searchViewId: false,
    });
    expect(`.o_searchview .o_searchview_facet`).toHaveCount(1);
    expect(searchBar.env.searchModel.groupBy).toEqual(["partner_id"]);
});

test("URL with multiple groupBy (incl. custom), creates and activates single groupBy", async () => {
    const urlSearch = fromUrl("?groupBy=" + encodeURIComponent('["state", "partner_id"]'));
    const searchBar = await mountWithSearch(SearchBar, {
        urlSearch,
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
    const urlSearch = fromUrl("?groupBy=" + encodeURIComponent('["date_order:year"]'));
    const searchBar = await mountWithSearch(SearchBar, {
        urlSearch,
        resModel: "mock.purchase.order",
        searchMenuTypes: ["groupBy"],
        searchViewId: false,
    });
    expect(searchBar.env.searchModel.groupBy).toEqual(["date_order:year"]);
});

test("URL with groupBy and orderBy activates ordered groupBy", async () => {
    const encodedgroupBy = encodeURIComponent('["partner_id"]');
    const encodedorderBy = encodeURIComponent('[{"name":"__count", "asc": false}]');
    const urlSearch = fromUrl("?groupBy=" + encodedgroupBy + "&orderBy=" + encodedorderBy);
    const searchBar = await mountWithSearch(SearchBar, {
        urlSearch,
        resModel: "mock.purchase.order",
        searchMenuTypes: ["groupBy"],
        searchViewId: false,
    });
    expect(`.o_searchview .o_searchview_facet`).toHaveCount(1);
    expect(`.o_searchview_facet_label .oi[data-icon='arrow_downward']`).toHaveCount(1); // OrderBy desc icon
    expect(searchBar.env.searchModel.groupBy).toEqual(["partner_id"]);
    expect(searchBar.env.searchModel.orderBy).toEqual([{ asc: false, name: "__count" }]);
});

test("URL with filter + groupBy + orderBy activates filters", async () => {
    const domain = encodeURIComponent('[["state", "=", "sent"]]');
    const groupBy = encodeURIComponent('["partner_id"]');
    const orderBy = encodeURIComponent('[{"name":"__count","asc":true}]');
    const url = "?domain=" + domain + "&groupBy=" + groupBy + "&orderBy=" + orderBy;
    const urlSearch = fromUrl(url);

    const searchBar = await mountWithSearch(SearchBar, {
        urlSearch,
        resModel: "mock.purchase.order",
        searchMenuTypes: ["groupBy"],
        searchViewId: false,
    });
    expect(`.o_searchview .o_searchview_facet`).toHaveCount(2); // One for the shared filter and one for the groupby
    expect(searchBar.env.searchModel.domain).toEqual([["state", "=", "sent"]]);
    expect(searchBar.env.searchModel.groupBy).toEqual(["partner_id"]);
    expect(`.o_searchview_facet_label .oi[data-icon='arrow_upward']`).toHaveCount(1); // OrderBy ascending icon
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
    const urlSearch = fromUrl(url);

    const searchBar = await mountWithSearch(SearchBar, {
        urlSearch,
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

    const urlSearch = fromUrl("?domain=" + encodeURIComponent('[["state", "=",]]'));

    const searchBar = await mountWithSearch(SearchBar, {
        urlSearch,
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
    const urlSearch = fromUrl("?domain=" + encodeURIComponent('[["state", "=", "sent"]]'));

    const searchBar = await mountWithSearch(SearchBar, {
        urlSearch,
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

test.tags("desktop");
test("hotkey sharing available after dialog", async () => {
    defineActions([
        {
            id: 1,
            name: "Some List View",
            type: "ir.actions.act_window",
            views: [[false, "list"]],
            res_model: "mock.purchase.order",
        },
        {
            id: 2,
            name: "Some Dialog",
            type: "ir.actions.act_window",
            target: "new",
            views: [[false, "form"]],
            res_model: "mock.purchase.order",
        },
    ]);

    MockPurchaseOrders._views = {
        form: `<form><field name="partner_id"/></form>`,
        list: `
            <list>
                <header> <button type="action" name="2" string="Button"/> </header>
                <field name="state"/>
            </list>`,
    };

    // We need to mount with WebClient because fiber rendering behaves
    // differently in simple MountView and the bug is harder to reproduce.
    // (we need OverlayContainer & ListRender in the same AnimationFrame)
    await mountWithCleanup(WebClient);

    // Check that hotkey is available by default
    await getService("action").doAction(1);
    await press(["control", "k"]);
    await animationFrame();
    expect(queryAllTexts(".o_command_hotkey").some((key) => key.includes(SHARE_KEY))).toBe(true);
    await press(["escape"]);

    // Select all records (making the searchBar disapear) and then open dialog.
    await contains(".o_list_record_selector div input").click();
    await contains('button[name="2"]').click();
    await contains(".btn-close").click();

    // The command should still be here (but isn't due to render issues)
    await press(["control", "k"]);
    await animationFrame();
    expect(queryAllTexts(".o_command_hotkey").some((key) => key.includes(SHARE_KEY))).toBe(true);
});

test.tags("desktop"); // mountView hides search Bar on mobile (but not mountWithSearch)
test("URL with single filter triggers RPC and filters record list", async () => {
    const encodedDomain = encodeURIComponent('[["state", "=", "sent"]]');
    const urlSearch = fromUrl("?domain=" + encodedDomain);
    // In this test we focus on the RPC which is triggered by mounting a view list
    let expectedDomain = [["state", "=", "sent"]];
    onRpc(async (params) => {
        if (params.method == "web_search_read") {
            expect.step("web_search_read");
            expect(params.kwargs.domain).toEqual(expectedDomain);
        }
    });
    await mountView({
        urlSearch,
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
    expect(queryAllTexts(".o_command_hotkey").some((key) => key.includes(SHARE_KEY))).toBe(false);
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
    expect(queryAllTexts(".o_command_hotkey").some((key) => key.includes(SHARE_KEY))).toBe(true);
});

test.tags("desktop"); // Shortcut testing only on computer
test("hotkey sharing after typing in command palette", async () => {
    await mountView({
        type: "list",
        resModel: "mock.purchase.order",
        arch: `<list> <field name="state"/> </list>`,
        config: { actionId: 1 }, // Just to let the search model know this is a stored action
    });

    await press(["control", "k"]);
    await waitFor(".o_command_palette");
    await contains(".o_command_palette_search input").click();
    await fill("S");
    await animationFrame();
    expect(queryAllTexts(".o_command_hotkey").some((key) => key.includes(SHARE_KEY))).toBe(true);
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

    await mountView({
        type: "list",
        resModel: "mock.purchase.order",
        arch: `<list> <field name="state"/> </list>`,
        config: { actionId: 1 }, // Just to let the search model know this is a stored action
    });

    await press(["alt", "shift", "h"]);
    await animationFrame();
    expect(clipboardWrites).toHaveLength(1);
    expect.verifySteps(["Success notification"]);
});

test.tags("desktop"); // Shortcut testing only on computer
test("hotkey sharing copies simple domain + groupBy to clipboard", async () => {
    // Less comprehensinve testing then decoding url, as we use the same helper
    // as when saving favorite filters to encode the search params in the url
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

    expect(clipboardWrites[0].split("?domain=")[1]).toBe(
        encodeURIComponent('[("state", "=", "draft")]') +
            "&groupBy=" +
            encodeURIComponent('["state"]')
    );
});

test.tags("desktop"); // Shortcut testing only on computer
test("hotkey sharing copies complex search to clipboard", async () => {
    // Less comprehensinve testing then decoding url, as we use the same helper
    // as when saving favorite filters to encode the search params in the url
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

    await contains(".oi[data-icon='swap_vert']", { visible: false }).click(); // Facet click to trigger orderBy
    await animationFrame();

    await press(["alt", "shift", "h"]);
    await animationFrame();

    expect(clipboardWrites[0].split("?domain=")[1]).toBe(
        encodeURIComponent(`["|", ("state", "=", "draft"), ("partner_id", "ilike", "%Juan%")]`) +
            "&groupBy=" +
            encodeURIComponent('["partner_id"]') +
            "&orderBy=" +
            encodeURIComponent('[{"name":"__count","asc":false}]')
    );
});

test.tags("desktop"); // Shortcut testing only on computer
test("hotkey sharing keeps a relative date filter relative in the URL", async () => {
    await mountView({
        type: "list",
        resModel: "mock.purchase.order",
        arch: `<list><field name="state"/></list>`,
        searchMenuTypes: ["filter"],
        searchViewArch: `
            <search>
                <filter string="Date" name="date_order" date="date_order"/>
            </search>
        `,
        config: { actionId: 1 },
    });

    await toggleSearchBarMenu();
    await toggleMenuItem("Date");
    await toggleMenuItemOption("Date", "This Week");

    await press(["alt", "shift", "h"]);
    await animationFrame();

    expect(decodeURIComponent(clipboardWrites[0].split("?domain=")[1].split("&")[0])).toBe(
        `["&", ("date_order", ">=", "today =week_start"), ("date_order", "<", "today =week_start +1w")]`
    );
});

test("URL with filter keeps the saved favorites available", async () => {
    const urlSearch = fromUrl("?domain=" + encodeURIComponent('[["state", "=", "sent"]]'));
    await mountWithSearch(SearchBar, {
        urlSearch,
        resModel: "mock.purchase.order",
        searchMenuTypes: ["filter", "favorite"],
        searchViewId: false,
        searchViewArch: `<search/>`,
        irFilters: [
            {
                context: "{}",
                domain: "[('state', '=', 'draft')]",
                id: 7,
                is_default: true,
                name: "My favorite",
                sort: "[]",
                user_ids: [2],
            },
        ],
    });
    // the shared filter is applied instead of the default favorite...
    expect(queryAllTexts(".o_searchview_facet")).toEqual(["Shared"]);
    // ...but the favorite can still be selected
    await toggleSearchBarMenu();
    expect(queryAllTexts(".o_favorite_menu .o_menu_item")).toEqual(["My favorite", "Save search"]);
    await toggleMenuItem("My favorite");
    expect(queryAllTexts(".o_searchview_facet")).toEqual(["My favorite"]);
});

/**
 * Search written live in the URL of the action
 */

function defineUrlSearchActions() {
    defineActions([
        {
            id: 1,
            name: "Purchase Orders",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [false, "kanban"],
            ],
            res_model: "mock.purchase.order",
        },
        {
            id: 2,
            name: "Other Purchase Orders",
            type: "ir.actions.act_window",
            views: [[false, "list"]],
            res_model: "mock.purchase.order",
        },
    ]);
    MockPurchaseOrders._views = {
        list: `<list><field name="state"/></list>`,
        kanban: `
            <kanban>
                <templates><t t-name="card"><field name="state"/></t></templates>
            </kanban>`,
        search: `
            <search>
                <filter string="Draft" name="draft" domain="[('state', '=', 'draft')]"/>
            </search>`,
    };
}

async function getUrlParams() {
    await runAllTimers();
    return new URL(location.href).searchParams;
}

test.tags("desktop");
test("default search is not written in the URL", async () => {
    defineUrlSearchActions();
    redirect("/odoo/action-1");
    await mountWebClient();
    expect(getFacetTexts()).toEqual([]);
    expect([...(await getUrlParams()).keys()]).toEqual([]);
});

test.tags("desktop");
test("search changes are written in the URL and kept on view switch", async () => {
    defineUrlSearchActions();
    redirect("/odoo/action-1");
    await mountWebClient();
    await toggleSearchBarMenu();
    await toggleMenuItem("Draft");
    let params = await getUrlParams();
    expect(new Domain(params.get("domain")).toList()).toEqual([["state", "=", "draft"]]);

    await switchView("kanban");
    params = await getUrlParams();
    expect(params.get("view_type")).toBe("kanban");
    expect(new Domain(params.get("domain")).toList()).toEqual([["state", "=", "draft"]]);

    await contains(".o_facet_remove").click();
    expect((await getUrlParams()).has("domain")).toBe(false);
});

test.tags("desktop");
test("search from the URL is applied, and kept in the URL", async () => {
    defineUrlSearchActions();
    redirect("/odoo/action-1?domain=" + encodeURIComponent('[["state", "=", "sent"]]'));
    await mountWebClient();
    expect(getFacetTexts()).toEqual(["Shared"]);
    expect(`.o_data_row`).toHaveCount(2);
    const params = await getUrlParams();
    expect(new Domain(params.get("domain")).toList()).toEqual([["state", "=", "sent"]]);
});

test.tags("desktop");
test("search from the URL is not applied to the action opened again or afterwards", async () => {
    defineUrlSearchActions();
    redirect("/odoo/action-1?domain=" + encodeURIComponent('[["state", "=", "sent"]]'));
    await mountWebClient();
    expect(getFacetTexts()).toEqual(["Shared"]);

    await getService("action").doAction(2);
    await animationFrame();
    expect(getFacetTexts()).toEqual([]);
    expect((await getUrlParams()).has("domain")).toBe(false);

    await getService("action").doAction(1, { clearBreadcrumbs: true });
    await animationFrame();
    expect(getFacetTexts()).toEqual([]);
    expect((await getUrlParams()).has("domain")).toBe(false);
});

test.tags("desktop");
test("search from the URL is not applied in a dialog", async () => {
    defineUrlSearchActions();
    redirect("/odoo/action-1?domain=" + encodeURIComponent('[["state", "=", "sent"]]'));
    await mountWebClient();
    getService("dialog").add(SelectCreateDialog, {
        resModel: "mock.purchase.order",
        title: "Select",
    });
    await animationFrame();
    expect(`.modal .o_list_view`).toHaveCount(1);
    expect(`.modal .o_searchview_facet`).toHaveCount(0);
    expect(`.modal .o_data_row`).toHaveCount(3);
});

test.tags("desktop");
test("search too long for the URL is applied but not written", async () => {
    defineUrlSearchActions();
    const values = Array.from({ length: 300 }, (_, i) => `"value ${i}"`).join(", ");
    const domain = `["|", ["state", "=", "sent"], ["state", "in", [${values}]]]`;
    redirect("/odoo/action-1?domain=" + encodeURIComponent(domain));
    await mountWebClient();
    expect(getFacetTexts()).toEqual(["Shared"]);
    expect(`.o_data_row`).toHaveCount(2);
    expect((await getUrlParams()).has("domain")).toBe(false);
});

test.tags("desktop");
test("search panel selection is not written in the URL", async () => {
    defineUrlSearchActions();
    MockPurchaseOrders._views.search = `
        <search>
            <filter string="Draft" name="draft" domain="[('state', '=', 'draft')]"/>
            <searchpanel>
                <field name="state" select="one"/>
            </searchpanel>
        </search>`;
    redirect("/odoo/action-1");
    await mountWebClient();
    await contains(`.o_search_panel_category_value:contains("Sent") header`).click();
    expect(`.o_data_row`).toHaveCount(2);
    expect((await getUrlParams()).has("domain")).toBe(false);

    // a facet is written, without the search panel domain
    await toggleSearchBarMenu();
    await toggleMenuItem("Draft");
    const params = await getUrlParams();
    expect(new Domain(params.get("domain")).toList()).toEqual([["state", "=", "draft"]]);
});
