import { Component, onWillStart, proxy, xml } from "@odoo/owl";
import { expect, test } from "@odoo/hoot";
import { animationFrame, runAllTimers } from "@odoo/hoot-mock";
import { mountWithCleanup, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { useService } from "@web/core/utils/hooks";
import { batchedOrmService } from "@analytic/services/batched_orm_service";
import { defineAnalyticModels } from "./analytic_test_helpers";

defineAnalyticModels();

class Probe extends Component {
    static template = xml`<span t-att-data-account="this.props.accountId" t-out="this.state.result"/>`;
    static props = ["accountId"];
    setup() {
        this.batchedOrm = useService("batchedOrm");
        this.state = proxy({ result: "pending" });
        onWillStart(async () => {
            const records = await this.batchedOrm.read(
                "account.analytic.account",
                [this.props.accountId],
                ["display_name"],
                {}
            );
            this.state.result = records[0]?.display_name ?? "not found";
        });
    }
}

class Parent extends Component {
    static template = xml`
        <div>
            <t t-foreach="this.state.rows" t-as="row" t-key="row.key">
                <Probe accountId="row.accountId"/>
            </t>
        </div>`;
    static components = { Probe };
    static props = ["*"];
    setup() {
        this.state = proxy({ rows: [] });
    }
}

test.only("a component destroyed mid-batch must prevent its still-alive siblings", async () => {
    onRpc("account.analytic.account", "read", () => [
        { id: 1, display_name: "Marketing" },
        { id: 2, display_name: "Sales" },
    ]);

    const releaseBatch = Promise.withResolvers();
    const originalStart = batchedOrmService.start;
    patchWithCleanup(batchedOrmService, {
        start() {
            const orm = originalStart.call(this);
            orm.batch = async function (ids, keys, callback) {
                const key = JSON.stringify(keys);
                if (!this.batches[key]) {
                    this.batches[key] = {
                        ids: [],
                        promise: releaseBatch.promise.then(() => callback(this.batches[key].ids)),
                    };
                }
                this.batches[key].ids.push(...ids);
                return this.batches[key].promise;
            };
            return orm;
        },
    });

    const parent = await mountWithCleanup(Parent);

    // "a" is rendered first: it becomes the batch's first caller.
    parent.state.rows = [
        { key: "a", accountId: 1 },
        { key: "b", accountId: 2 },
    ];
    await animationFrame();

    // "a" is destroyed while the batch's dispatch is still held back.
    parent.state.rows = [{ key: "b", accountId: 2 }];
    await animationFrame();

    releaseBatch.resolve();
    await animationFrame();
    await runAllTimers();
    await animationFrame();

    expect("[data-account='2']").toHaveText("Sales");
});
