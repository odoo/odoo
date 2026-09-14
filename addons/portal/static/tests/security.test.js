import { expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import {
    handleCheckIdentity,
    IdentityCheckCancelled,
} from "@portal/interactions/portal_security";
import { contains, getService, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ConnectionLostError, RPCError } from "@web/core/network/rpc";
import { MainComponentsContainer } from "@web/ui/main_components_container";

async function prepareCheck(call) {
    await mountWithCleanup(MainComponentsContainer);
    const result = handleCheckIdentity(
        Promise.resolve({
            type: "ir.actions.act_window",
            res_model: "res.users.identitycheck",
            res_id: 42,
        }),
        {
            write: async (model, ids, values) => {
                expect(model).toBe("res.users.identitycheck");
                expect(ids).toEqual([42]);
                expect(values).toEqual({ auth_method: "password" });
            },
            call,
        },
        getService("dialog"),
    );
    // Observe failures immediately, including dismissal during a pending check.
    const outcome = result.then(
        (value) => ({ value }),
        (error) => ({ error }),
    );
    await animationFrame();
    return { outcome };
}

test("identity validation keeps the server message and allows a corrected password", async () => {
    let calls = 0;
    const { outcome } = await prepareCheck(async () => {
        if (++calls === 1) {
            const error = new RPCError("invalid password");
            error.data = {
                name: "odoo.exceptions.UserError",
                message: "Incorrect Password",
            };
            throw error;
        }
        return { completed: true };
    });
    await contains('input[type="password"]').edit("wrong", { confirm: false });
    await contains(".modal-footer .btn-primary").click();
    expect(queryOne("input").validationMessage).toBe("Incorrect Password");
    await contains('input[type="password"]').edit("correct", { confirm: false });
    expect(queryOne("input").validationMessage).toBe("");
    await contains(".modal-footer .btn-primary").click();
    expect(await outcome).toEqual({ value: { completed: true } });
    expect(".modal").toHaveCount(0);
});

test("connection failures reject the guarded operation instead of blaming the password", async () => {
    const failure = new ConnectionLostError();
    const { outcome } = await prepareCheck(async () => {
        throw failure;
    });
    await contains('input[type="password"]').edit("password", { confirm: false });
    await contains(".modal-footer .btn-primary").click();
    expect((await outcome).error).toBe(failure);
    expect(".modal").toHaveCount(0);
});

test("dismissing the identity dialog rejects with cancellation", async () => {
    const { outcome } = await prepareCheck(() => expect.step("unexpected check"));
    await contains(".modal-footer .btn-secondary").click();
    expect((await outcome).error).toBeInstanceOf(IdentityCheckCancelled);
    expect.verifySteps([]);
});
