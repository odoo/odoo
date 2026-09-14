import { passkeyLib } from "@auth_passkey/passkey_lib";
import { PortalPasskey } from "@auth_portal/interactions/passkey";
import { PortalPasskeyCreate } from "@auth_portal/interactions/passkey_create";
import { RevokeAllTrustedDevices } from "@auth_portal/interactions/revoke_all_trusted_devices";
import { TOTPDisable } from "@auth_portal/interactions/totp_disable";
import { TOTPEnable } from "@auth_portal/interactions/totp_enable";
import { expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { getInteraction, startInteraction } from "@web/../tests/public/helpers";
import {
    contains,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { makeLogger } from "@web/core/debug/debug_logger";
import { RPCError } from "@web/core/network/rpc";
import { Deferred } from "@web/core/utils/concurrency";
import { MainComponentsContainer } from "@web/ui/main_components_container";

const log = makeLogger("portal.auth.tests");
const createMarkup = '<button id="portal_passkey_add">Create</button>';
async function prepare(I, markup) {
    const { core } = await startInteraction(I, markup);
    await mountWithCleanup(MainComponentsContainer);
    return getInteraction(core, I);
}

test("failed WebAuthn registration never creates a key wizard", async () => {
    const interaction = await prepare(PortalPasskeyCreate, createMarkup);
    patchWithCleanup(passkeyLib, {
        startRegistration: async () => {
            throw new Error("registration cancelled");
        },
    });
    patchWithCleanup(console, {
        error: () => log.logic("registration error reported"),
    });
    patchWithCleanup(interaction.services.orm, {
        create: async () => {
            expect.step("unexpected wizard creation");
            throw new Error("unexpected wizard creation");
        },
    });
    await expect(interaction.createPasskey({}, "Key")).rejects.toThrow(
        "registration cancelled",
    );
    expect.verifySteps([]);
});

test("the passkey naming dialog waits for its registration action", async () => {
    const interaction = await prepare(PortalPasskeyCreate, createMarkup);
    patchWithCleanup(interaction.services.orm, {
        call: async () => ({ context: { registration: {} } }),
    });
    const registration = new Deferred();
    patchWithCleanup(interaction, { createPasskey: () => registration });
    await interaction.startRegistrationFlow();
    await animationFrame();
    await contains('input[name="keyname"]').edit("Key", { confirm: false });
    await contains(".modal-footer .btn-primary").click();
    expect(".modal-footer .btn-primary").toHaveProperty("disabled", true);
    registration.resolve();
    await animationFrame();
    expect(".modal").toHaveCount(0);
});

for (const [name, I, markup, method] of [
    ["create passkey", PortalPasskeyCreate, createMarkup, "startRegistrationFlow"],
    [
        "delete passkey",
        PortalPasskey,
        '<div class="o_passkey_portal_entry" id="42"><span class="o_passkey_name">Key</span></div>',
        "onDelete",
    ],
    [
        "enable TOTP",
        TOTPEnable,
        '<button id="auth_portal_totp_enable">Enable</button>',
        "onClick",
    ],
    [
        "disable TOTP",
        TOTPDisable,
        '<button id="auth_portal_totp_disable">Disable</button>',
        "onClick",
    ],
    [
        "revoke trusted devices",
        RevokeAllTrustedDevices,
        '<button id="auth_portal_revoke_all_devices">Revoke</button>',
        "onClick",
    ],
]) {
    test(`${name}: cancelling identity verification ends the action quietly`, async () => {
        const interaction = await prepare(I, markup);
        patchWithCleanup(interaction.services.orm, {
            call: async () => {
                expect.step("identity requested");
                return {
                    type: "ir.actions.act_window",
                    res_model: "res.users.identitycheck",
                    res_id: 42,
                };
            },
            write: async () => {},
        });
        const outcome = interaction[method]().then(
            (value) => ({ value }),
            (error) => ({ error }),
        );
        await animationFrame();
        await contains(".modal-footer .btn-secondary").click();
        expect(await outcome).toEqual({ value: undefined });
        expect(".modal").toHaveCount(0);
        expect.verifySteps(["identity requested"]);
    });
}

async function prepareTOTP(enable) {
    const interaction = await prepare(
        TOTPEnable,
        `
        <button id="auth_portal_totp_enable">Enable</button>
        <script id="totp_wizard_view" type="text/xml"><form><sheet><div><field name="code"/></div></sheet></form></script>`,
    );
    patchWithCleanup(interaction.services.orm, {
        call: async (model, method) => {
            if (method === "action_totp_enable_wizard") {
                return { res_model: "auth_totp.wizard", res_id: 42 };
            }
            return enable();
        },
        read: async () => [{ id: 42 }],
        write: async () => {},
    });
    await interaction.onClick();
    await animationFrame();
    await contains('input[name="code"]').edit("123456", { confirm: false });
}

test("a rejected TOTP code displays the server validation message", async () => {
    await prepareTOTP(() => {
        const error = new RPCError("Invalid code");
        error.data = { name: "odoo.exceptions.UserError", message: "Invalid code" };
        throw error;
    });
    await contains(".modal-footer .btn-primary").click();
    expect(queryOne('input[name="code"]').validationMessage).toBe("Invalid code");
    await contains('input[name="code"]').edit("654321", { confirm: false });
    expect(queryOne('input[name="code"]').validationMessage).toBe("");
});

test("cancelling nested identity verification leaves TOTP activation retryable", async () => {
    await prepareTOTP(() => ({
        type: "ir.actions.act_window",
        res_model: "res.users.identitycheck",
        res_id: 42,
    }));
    await contains(".modal-footer .btn-primary").click();
    expect(".modal").toHaveCount(2);
    const passwordForm = queryOne('input[type="password"]').closest(".modal");
    passwordForm.querySelector(".btn-secondary").click();
    await animationFrame();
    expect(".modal").toHaveCount(1);
    expect(queryOne('input[name="code"]').validationMessage).toBe("");
    expect(".modal-footer .btn-primary").toHaveProperty("disabled", false);
});
