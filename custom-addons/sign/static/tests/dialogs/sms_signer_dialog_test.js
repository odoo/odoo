/** @odoo-module **/

import { click, getFixture, mount, patchWithCleanup, nextTick } from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import {
    makeFakeUserService,
    makeFakeDialogService,
    makeFakeLocalizationService,
} from "@web/../tests/helpers/mock_services";
import { SMSSignerDialog } from "@sign/dialogs/dialogs";
import { registry } from "@web/core/registry";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { uiService } from "@web/core/ui/ui_service";

const serviceRegistry = registry.category("services");
let target;

const fakePhoneNumber = "123456789";
const documentId = 23;
const signRequestItemToken = "abc";
const fakeCode = "1234";

QUnit.module("sms signer dialog", (hooks) => {
    const mountSMSSignerDialog = async (mockRPC, postValidation = () => {}) => {
        const env = await makeTestEnv({ mockRPC });
        env.dialogData = {
            isActive: true,
            close: () => {},
        };

        await mount(SMSSignerDialog, target, {
            props: {
                signerPhone: fakePhoneNumber,
                postValidation: postValidation,
                close: () => {},
            },
            env,
        });
    };

    hooks.beforeEach(async () => {
        target = getFixture();
        serviceRegistry.add("user", makeFakeUserService());
        serviceRegistry.add("dialog", makeFakeDialogService());
        serviceRegistry.add("localization", makeFakeLocalizationService());
        serviceRegistry.add("ui", uiService);
        serviceRegistry.add("hotkey", hotkeyService);
        const signInfo = {
            documentId,
            signRequestItemToken,
        };
        serviceRegistry.add("signInfo", {
            name: "signInfo",
            start() {
                return {
                    get(key) {
                        return signInfo[key];
                    },
                };
            },
        });
    });

    QUnit.test("SMS Signer Dialog should be rendered", async (assert) => {
        const mockRPC = async (route) => {
            if (
                route === `/sign/send-sms/${documentId}/${signRequestItemToken}/${fakePhoneNumber}`
            ) {
                assert.step("sms-sent");
                await nextTick();
                assert.containsOnce(
                    target,
                    "button:contains('SMS Sent')",
                    "should show 'SMS sent' while sending SMS"
                );
                return new Promise((res, rej) => {
                    browser.setTimeout(() => res(true), 1000);
                });
            }
        };

        await mountSMSSignerDialog(mockRPC, (code) => {
            assert.step("post-validation");
            assert.strictEqual(code, fakeCode, "post validation should be called with same code");
        });

        assert.containsOnce(target, ".o_sign_validate_sms", "should render verify SMS button");
        assert.containsOnce(target, ".o_sign_resend_sms");
        assert.containsOnce(target, "input[name='phone']");
        assert.strictEqual(target.querySelector("input[name='phone']").value, fakePhoneNumber);

        await click(target.querySelector("button.o_sign_resend_sms"));

        assert.verifySteps(["sms-sent"]);

        target.querySelector("#o_sign_public_signer_sms_input").value = fakeCode;
        await click(target.querySelector(".o_sign_validate_sms"));
        assert.verifySteps(["post-validation"]);
    });

    QUnit.test("SMS Signer Dialog should handle errors", async (assert) => {
        const mockRPC = (route) => {
            if (
                route === `/sign/send-sms/${documentId}/${signRequestItemToken}/${fakePhoneNumber}`
            ) {
                assert.step("sms-failed");
                return false;
            }
        };

        patchWithCleanup(SMSSignerDialog.prototype, {
            handleSMSError: () => {
                assert.step("handle-sms-error");
            },
        });

        await mountSMSSignerDialog(mockRPC);

        await click(target.querySelector("button.o_sign_resend_sms"));

        assert.verifySteps(["sms-failed", "handle-sms-error"]);
    });

    QUnit.test("SMS Signer Dialog timeout should enable re-send button", async (assert) => {
        const mockRPC = (route) => {
            if (
                route === `/sign/send-sms/${documentId}/${signRequestItemToken}/${fakePhoneNumber}`
            ) {
                return true;
            }
        };

        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });

        await mountSMSSignerDialog(mockRPC);

        await click(target.querySelector("button.o_sign_resend_sms"));
        assert.containsOnce(
            target,
            "button:contains('Re-send SMS')",
            "re-send sms button should be rendered"
        );
    });
});
