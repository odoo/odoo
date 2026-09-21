import { expect, test } from "@odoo/hoot";
import { click, queryFirst } from "@odoo/hoot-dom";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import { ReceptionReportLine } from "@stock/components/reception_report_line/stock_reception_report_line";
import { makeMockEnv, mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";

async function mountLine(data = {}) {
    const env = await makeMockEnv();
    await mountWithCleanup(ReceptionReportLine, {
        env,
        props: {
            data: {
                index: 0,
                product: { display_name: "Product" },
                quantity: 2,
                uom: "Units",
                move_out_id: 9,
                move_ins: [10],
                is_qty_assignable: true,
                is_assigned: false,
                source: ["WH/IN/0001"],
                ...data,
            },
            labelReport: {},
            parentIndex: "0",
            showUom: false,
            precision: 2,
            hasMovesIn: true,
        },
    });
    return env;
}

test("double-click on Assign fires a single RPC and disables the button", async () => {
    const rpcDone = new Deferred();
    onRpc("action_assign", async () => {
        expect.step("assign-rpc");
        await rpcDone;
        return true;
    });
    const env = await mountLine();
    env.bus.addEventListener("update-assign-state", ({ detail }) => {
        expect.step(`assigned:${detail.isAssigned}`);
    });

    const assignButton = queryFirst("button[name=assign_link]");
    await click(assignButton);
    await animationFrame();
    expect(assignButton).toHaveAttribute("disabled");
    await click(assignButton);
    await animationFrame();
    rpcDone.resolve();
    await animationFrame();
    expect.verifySteps(["assign-rpc", "assigned:true"]);
    expect(assignButton).not.toHaveAttribute("disabled");
});

test("unassign only flips the state when the server confirms", async () => {
    onRpc("action_unassign", () => {
        expect.step("unassign-rpc");
        return false;
    });
    const env = await mountLine({ is_assigned: true });
    env.bus.addEventListener("update-assign-state", () => expect.step("state-flipped"));
    await click("button[name=unassign_link]");
    await animationFrame();
    expect.verifySteps(["unassign-rpc"]);
});
