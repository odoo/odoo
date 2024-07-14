/** @odoo-module **/

import { click, getFixture, mount } from "@web/../tests/helpers/utils";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import {
    makeFakeUserService,
    makeFakeDialogService,
    makeFakeLocalizationService,
} from "@web/../tests/helpers/mock_services";
import { SignNameAndSignatureDialog } from "@sign/dialogs/dialogs";
import { registry } from "@web/core/registry";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { uiService } from "@web/core/ui/ui_service";

const serviceRegistry = registry.category("services");

let target;
const name = "Brandon Freeman";
const hash = "abcdef...";

QUnit.module("Sign Name and Signature Dialog", function (hooks) {
    const mountSignNameAndSignatureDialog = async () => {
        const mockRPC = async (route) => {
            if (route === "/web/sign/get_fonts/") {
                return {};
            }
        };
        const env = await makeTestEnv({ mockRPC });
        env.dialogData = {
            isActive: true,
            close: () => {},
        };
        await mount(SignNameAndSignatureDialog, target, {
            props: {
                signature: {
                    name,
                },
                frame: {},
                signatureType: "signature",
                displaySignatureRatio: 1,
                activeFrame: true,
                defaultFrame: "",
                mode: "auto",
                hash,
                onConfirm: () => {},
                onConfirmAll: () => {},
                onCancel: () => {},
                close: () => {},
            },
            env,
        });
    };

    hooks.beforeEach(() => {
        target = getFixture();
        serviceRegistry.add("dialog", makeFakeDialogService());
        serviceRegistry.add("localization", makeFakeLocalizationService());
        serviceRegistry.add("ui", uiService);
        serviceRegistry.add("hotkey", hotkeyService);
    });

    QUnit.test("sign name and signature dialog renders correctly", async function (assert) {
        const hasGroup = () => true;
        serviceRegistry.add("user", makeFakeUserService(hasGroup));

        await mountSignNameAndSignatureDialog();

        assert.deepEqual(
            [...target.querySelectorAll(".btn-primary, .btn-secondary")].map(
                (el) => el.textContent
            ),
            ["Sign all", "Sign", "Cancel"],
            "should show buttons"
        );
        assert.containsOnce(target, ".mt16", "should show legal info about using odoo signature");
        assert.strictEqual(
            target.querySelector('input[name="signer"]').value,
            name,
            "Should auto-fill the name"
        );
        assert.containsOnce(target, ".form-check", "should show frame in dialog");
        assert.notOk(
            target.querySelector(".form-check").classList.contains("d-none"),
            "frame should be shown"
        );
        assert.containsOnce(target, ".o_sign_frame.active");
        assert.strictEqual(
            target.querySelector(".o_sign_frame.active p").getAttribute("hash"),
            hash,
            "hash should be in the signature dialog"
        );
    });

    QUnit.test(
        "sign name and signature dialog - frame is hidden when user is not from the sign user group",
        async (assert) => {
            const hasGroup = () => false;
            serviceRegistry.add("user", makeFakeUserService(hasGroup));

            await mountSignNameAndSignatureDialog();

            assert.ok(
                target.querySelector(".form-check").classList.contains("d-none"),
                "frame should be hidden"
            );
        }
    );

    QUnit.test(
        "sign name and signature dialog toggles active class on frame input change",
        async function (assert) {
            const hasGroup = () => true;
            serviceRegistry.add("user", makeFakeUserService(hasGroup));

            await mountSignNameAndSignatureDialog();

            assert.ok(target.querySelector(".o_sign_frame").classList.contains("active"));
            await click(target, ".form-check-input");
            assert.notOk(
                target.querySelector(".o_sign_frame").classList.contains("active"),
                "should hide frame"
            );
            await click(target, ".form-check-input");
            assert.ok(target.querySelector(".o_sign_frame").classList.contains("active"));
        }
    );
});
