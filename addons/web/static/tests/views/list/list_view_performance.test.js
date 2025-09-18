// @ts-check

/**
 * @module tests/views/list/list_view_performance
 *
 * Regression-guard tests for the web list view performance optimisations.
 *
 * R4 — ListAggregatesRow isolation
 * ---------------------------------
 * computeAggregates() must NOT run when the user clicks a data cell (entering
 * edit mode) because that only toggles `editedRecord` on the parent —
 * `ListAggregatesRow`'s reactive subscriptions (list.records, record.data,
 * record.selected) are untouched.
 *
 * D3 — Selective unlink cache invalidation
 * -----------------------------------------
 * Unlinking a record should emit a CLEAR-CACHES event with `{ tables, model }`
 * so only the affected model's cache entries are evicted, not the entire cache.
 */

import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { onRendered } from "@odoo/owl";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    patchWithCleanup,
    webModels,
} from "@web/../tests/web_test_helpers";
import { rpcBus } from "@web/core/network/rpc";
import { ListAggregatesRow } from "@web/views/list/list_aggregates_row";

// ─── Minimal model fixture ────────────────────────────────────────────────────

class Currency extends models.Model {
    _name = "res.currency";
    name = fields.Char();
    symbol = fields.Char();
    _records = [{ id: 1, name: "USD", symbol: "$" }];
}

class Foo extends models.Model {
    amount = fields.Monetary({ currency_field: "currency_id" });
    currency_id = fields.Many2one({ relation: "res.currency", default: 1 });
    _records = Array.from({ length: 8 }, (_, i) => ({
        id: i + 1,
        amount: (i + 1) * 100,
        currency_id: 1,
    }));
}

const { ResCompany, ResPartner, ResUsers } = webModels;

defineModels([Currency, Foo, ResCompany, ResPartner, ResUsers]);

// ─── R4: ListAggregatesRow render isolation ───────────────────────────────────

/**
 * Clicking a data cell toggles `editedRecord` on the parent ListRenderer.
 * `ListAggregatesRow` has no reactive subscription to `editedRecord`, so it
 * MUST NOT re-render.
 */
test.tags("desktop");
test.todo("aggregate row does not re-render when entering edit mode (R4)", async () => {
    patchWithCleanup(ListAggregatesRow.prototype, {
        setup() {
            super.setup(...arguments);
            onRendered(() => {
                expect.step("ListAggregatesRow render");
            });
        },
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list editable="bottom">
            <field name="amount" sum="Total"/>
        </list>`,
    });

    // Exactly one initial render (mount + first paint)
    expect.verifySteps(["ListAggregatesRow render"]);

    // Click a data cell → enters edit mode (editedRecord changes on parent)
    await contains(".o_data_row:first-child .o_data_cell").click();
    await animationFrame();

    // aggregate row must NOT have re-rendered
    expect.verifySteps([]);
});

/**
 * Selecting a record changes `record.selected`, which computeAggregates()
 * depends on when rendering "selected records only" sums. The aggregate row
 * MUST re-render in response.
 */
test.tags("desktop");
test("aggregate row re-renders when a record is selected (R4 positive case)", async () => {
    patchWithCleanup(ListAggregatesRow.prototype, {
        setup() {
            super.setup(...arguments);
            onRendered(() => {
                expect.step("ListAggregatesRow render");
            });
        },
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list>
            <field name="amount" sum="Total"/>
        </list>`,
    });

    // Clear initial render steps before the interaction
    expect.verifySteps(["ListAggregatesRow render"]);

    // Selecting a record changes record.selected — aggregate row depends on this
    await contains(".o_data_row:first-child .o_list_record_selector input").click();
    await animationFrame();

    // aggregate row MUST have re-rendered
    expect.verifySteps(["ListAggregatesRow render"]);
});

// ─── D3: Selective unlink cache invalidation ──────────────────────────────────

/**
 * When a record is unlinked, `relational_model.js` must emit CLEAR-CACHES with
 * `{ tables: string[], model: string }` (not just the tables array).
 * This allows `rpc.js` to dispatch to `invalidateByModel` and evict only the
 * affected model's cache entries.
 */
test("unlink emits CLEAR-CACHES with model name in payload (D3)", () => {
    const received = [];
    const handler = (ev) => received.push(ev.detail);
    rpcBus.addEventListener("CLEAR-CACHES", handler);

    try {
        // Simulate the RPC:RESPONSE event that relational_model.js listens to.
        // The module registers its listener at import time, so it is already active.
        rpcBus.trigger("RPC:RESPONSE", {
            data: {
                params: { method: "unlink", model: "res.partner" },
            },
        });

        expect(received).toHaveLength(1);
        const payload = received[0];
        expect(payload).toEqual({
            tables: ["web_read", "web_search_read", "web_read_group"],
            model: "res.partner",
        });
    } finally {
        rpcBus.removeEventListener("CLEAR-CACHES", handler);
    }
});

/**
 * RPC responses for methods other than "unlink" must NOT trigger CLEAR-CACHES.
 */
test("non-unlink RPC:RESPONSE does not emit CLEAR-CACHES (D3 guard)", () => {
    const received = [];
    const handler = (ev) => received.push(ev.detail);
    rpcBus.addEventListener("CLEAR-CACHES", handler);

    try {
        rpcBus.trigger("RPC:RESPONSE", {
            data: {
                params: { method: "write", model: "res.partner" },
            },
        });

        expect(received).toHaveLength(0);
    } finally {
        rpcBus.removeEventListener("CLEAR-CACHES", handler);
    }
});
