import { Component, proxy, xml } from "@odoo/owl";
import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";
import { useService } from "@web/core/utils/hooks";
import { defineAnalyticModels } from "./analytic_test_helpers";

defineAnalyticModels();

const accountNames = {};

class AccountName extends Component {
    static template = xml`<span t-att-data-account="this.props.accountId" t-out="this.state.name"/>`;
    static props = ["accountId"];
    setup() {
        this.batchedOrm = useService("batchedOrm");
        this.state = proxy({ name: "" });
        accountNames[this.props.accountId] = this;
    }
    async load() {
        const [record] = await this.batchedOrm.read(
            "account.analytic.account",
            [this.props.accountId],
            ["display_name"]
        );
        this.state.name = record.display_name;
    }
}

class Parent extends Component {
    static template = xml`
        <t t-foreach="this.state.accountIds" t-as="accountId" t-key="accountId">
            <AccountName accountId="accountId"/>
        </t>`;
    static components = { AccountName };
    static props = ["*"];
    setup() {
        this.state = proxy({ accountIds: [1, 2] });
    }
}

test("destroying the first caller of a batch does not break the other callers", async () => {
    const readDone = Promise.withResolvers();
    onRpc("account.analytic.account", "read", async () => {
        expect.step("read");
        await readDone.promise;
        return [
            { id: 1, display_name: "Marketing" },
            { id: 2, display_name: "Sales" },
        ];
    });
    const parent = await mountWithCleanup(Parent);

    accountNames[1].load();
    accountNames[2].load();
    await animationFrame();
    expect.verifySteps(["read"]);

    parent.state.accountIds = [2];
    await animationFrame();
    expect("[data-account]").toHaveCount(1);

    readDone.resolve();
    await animationFrame();
    expect("[data-account='2']").toHaveText("Sales");
    expect.verifySteps([]);
});
