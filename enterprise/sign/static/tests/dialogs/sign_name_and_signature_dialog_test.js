/** @odoo-module **/

import { click, getFixture, nextTick, editInput } from "@web/../tests/helpers/utils";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import {
    makeFakeDialogService,
    makeFakeLocalizationService,
    patchUserWithCleanup,
} from "@web/../tests/helpers/mock_services";
import { SignNameAndSignatureDialog } from "@sign/dialogs/dialogs";
import { registry } from "@web/core/registry";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { uiService } from "@web/core/ui/ui_service";
import { popoverService } from "@web/core/popover/popover_service";
import { mountInFixture } from "@web/../tests/helpers/mount_in_fixture";

const serviceRegistry = registry.category("services");

let target;
const name = "Brandon Freeman";
const hash = "abcdef...";

QUnit.module("Sign Name and Signature Dialog", function (hooks) {
    const mountSignNameAndSignatureDialog = async () => {
        const mockRPC = async (route) => {
            if (route.includes("/web/sign/get_fonts/")) {
                return {};
            }
        };
        const env = await makeTestEnv({ mockRPC });
        env.dialogData = {
            isActive: true,
            close: () => {},
        };
        await mountInFixture(SignNameAndSignatureDialog, target, {
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
        serviceRegistry.add("popover", popoverService);
    });

    QUnit.test("sign name and signature dialog renders correctly", async function (assert) {
        const hasGroup = async () => true;
        patchUserWithCleanup({ hasGroup });

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
            const hasGroup = async () => true;
            patchUserWithCleanup({ hasGroup });

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

    QUnit.test(
        "sign name and signature dialog default font",

        async function (assert) {
            const mountSignNameAndSignatureDialogSaved = async () => {
                const mockRPC = async (route) => {
                    if (route.includes("/web/sign/get_fonts/")) {
                        assert.step(route);
                        return [];
                    }
                };
                const env = await makeTestEnv({ mockRPC });
                env.dialogData = {
                    isActive: true,
                    close: () => {},
                };
                await mountInFixture(SignNameAndSignatureDialog, target, {
                    props: {
                        signature: {
                            name
                        },
                        frame: {},
                        signatureType: "signature",
                        signatureImage: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+BCQAHBQICJmhD1AAAAABJRU5ErkJggg==",
                        displaySignatureRatio: 1,
                        activeFrame: true,
                        defaultFrame: "",
                        mode: "draw",
                        hash,
                        onConfirm: () => {},
                        onConfirmAll: () => {},
                        onCancel: () => {},
                        close: () => {},
                    },
                    env,
                });
            };

            const hasGroup = async () => true;
            patchUserWithCleanup({ hasGroup });
            await mountSignNameAndSignatureDialogSaved();
            await click(target, ".o_web_sign_auto_button");
            assert.verifySteps(["/web/sign/get_fonts/LaBelleAurore-Regular.ttf", "/web/sign/get_fonts/"]);
        }
    );

    QUnit.test(
        "sign name and signature dialog draw mode does not allow to submit sign with no sign drawn",
        async function (assert) {
            await mountSignNameAndSignatureDialog();
            const buttons = document.querySelector("footer.modal-footer > button.btn-primary");

            assert.ok(target.querySelector(".o_web_sign_auto_button").classList.contains("active"));
            assert.hasAttrValue(
                buttons,
                "disabled",
                undefined,
                "Buttons should not be disabled on auto when Full name and Signature are filled"
            );

            await nextTick();
            await click(target, ".o_web_sign_draw_button");
            assert.hasAttrValue(
                buttons,
                "disabled",
                "disabled",
                "Buttons should be disabled on draw if no signature is drawn"
            );
        }
    );

    QUnit.test(
        "sign name and signature dialog - auto mode disables button on whitespace-only name",
        async function (assert) {
            const hasGroup = async () => true;
            patchUserWithCleanup({ hasGroup });

            await mountSignNameAndSignatureDialog();
            const buttons = target.querySelectorAll(
                "footer.modal-footer > button.btn-primary, footer.modal-footer > button.btn-secondary"
            );

            const signAllButton = buttons[0]; // "Sign all"
            const signButton = buttons[1]; // "Sign"
            assert.notOk(signAllButton.disabled, "Sign all starts enabled");

            await editInput(target, 'input[name="signer"]', " ");

            assert.ok(signAllButton.disabled, "Sign all disabled on whitespace name");
            assert.ok(signButton.disabled, "Sign disabled on whitespace name");
        }
    );
});
