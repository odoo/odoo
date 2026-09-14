import { expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { PortalHomeCounters } from "@portal/interactions/portal_home_counters";
import { startInteraction } from "@web/../tests/public/helpers";
import { onRpc } from "@web/../tests/web_test_helpers";

test("duplicate placeholders share a request and all receive the counter", async () => {
    onRpc("/my/counters", async (request) => {
        const { params } = await request.json();
        expect(params.counters).toEqual(["order_count"]);
        expect.step("counters");
        return { order_count: 3 };
    });
    await startInteraction(
        PortalHomeCounters,
        `<div class="o_portal_my_home">
        <div class="o_portal_index_card d-none"><span data-placeholder_count="order_count"/></div>
        <div class="o_portal_index_card d-none"><span data-placeholder_count="order_count"/></div>
        <span class="o_portal_doc_spinner"/>
    </div>`,
    );
    expect.verifySteps(["counters"]);
    expect(queryAllTexts("[data-placeholder_count]")).toEqual(["3", "3"]);
    expect(".o_portal_index_card.d-none").toHaveCount(0);
    expect(".o_portal_doc_spinner").toHaveCount(0);
});

test("no placeholders need no RPC", async () => {
    onRpc("/my/counters", () => expect.step("unexpected request"));
    await startInteraction(
        PortalHomeCounters,
        '<div class="o_portal_my_home"><span class="o_portal_doc_spinner"/></div>',
    );
    expect.verifySteps([]);
    expect(".o_portal_doc_spinner").toHaveCount(0);
});

test("counter batches cover each unique name once with at most three requests", async () => {
    const names = Array.from({ length: 17 }, (_, index) => `counter_${index}`);
    const requested = [];
    let calls = 0;
    onRpc("/my/counters", async (request) => {
        const { params } = await request.json();
        calls++;
        requested.push(...params.counters);
        return Object.fromEntries(params.counters.map((name) => [name, 0]));
    });
    await startInteraction(
        PortalHomeCounters,
        `<div class="o_portal_my_home">${names.map((name) => `<div class="o_portal_index_card"><span data-placeholder_count="${name}"></span></div>`).join("")}</div>`,
    );
    expect(calls).toBe(3);
    expect(requested.sort()).toEqual([...names].sort());
    expect(".o_portal_index_card.d-none").toHaveCount(17);
});

test("always-visible zero counters and selector characters are supported", async () => {
    class Counters extends PortalHomeCounters {
        getCountersAlwaysDisplayed() {
            return ["quote'count"];
        }
    }
    onRpc("/my/counters", () => ({ "quote'count": 0, unknown: 12 }));
    await startInteraction(
        Counters,
        `<div class="o_portal_my_home"><div class="o_portal_index_card d-none"><span data-placeholder_count="quote'count"></span></div></div>`,
    );
    expect("[data-placeholder_count]").toHaveText("0");
    expect(".o_portal_index_card").not.toHaveClass("d-none");
});
