/** @odoo-module **/

import { click, getFixture, mount, editInput, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import {
    makeFakeDialogService,
    makeFakeLocalizationService,
} from "@web/../tests/helpers/mock_services";
import { SignRefusalDialog, ThankYouDialog } from "@sign/dialogs/dialogs";
import { registry } from "@web/core/registry";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { uiService } from "@web/core/ui/ui_service";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

const serviceRegistry = registry.category("services");
const documentId = 23;
const signRequestItemToken = "abc";
let target;

QUnit.module("sign refusal dialog", function (hooks) {
    const createEnvForDialog = async (mockRPC = {}) => {
        const env = await makeTestEnv({ mockRPC });
        env.dialogData = {
            isActive: true,
            close: () => {},
        };
        return env;
    };

    const mountSignRefusalDialog = async (env) => {
        await mount(SignRefusalDialog, target, {
            props: {
                close: () => {},
            },
            env,
        });
    };

    hooks.beforeEach(function () {
        target = getFixture();
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

    QUnit.test("sign refusal dialog should render", async function (assert) {
        await mountSignRefusalDialog(await createEnvForDialog());

        assert.containsOnce(target, ".o_sign_refuse_confirm_message", "should show textarea");
        assert.containsOnce(target, "button.refuse-button", "should show button");
        assert.strictEqual(
            target.querySelector("button.refuse-button").disabled,
            true,
            "button should be disabled at first render"
        );
    });

    QUnit.test(
        "sign refusal dialog should call refuse route when confirmed",
        async function (assert) {
            const mockRPC = (route) => {
                if (route === `/sign/refuse/${documentId}/${signRequestItemToken}`) {
                    assert.step("refuse-route-called");
                    return true;
                }
            };

            const env = await createEnvForDialog(mockRPC);
            patchWithCleanup(env.services.dialog, {
                add(component, props) {
                    if (component === ThankYouDialog) {
                        assert.step("thank-you-dialog");
                    }
                },
            });

            await mountSignRefusalDialog(env);

            await editInput(target, ".o_sign_refuse_confirm_message", "reason for refusal");
            assert.strictEqual(
                target.querySelector("button.refuse-button").disabled,
                false,
                "button should be enabled after textarea is filled"
            );
            await click(target.querySelector("button.refuse-button"));

            assert.verifySteps(["refuse-route-called", "thank-you-dialog"]);
        }
    );

    QUnit.test(
        "sign refusal dialog should show error dialog when rpc fails",
        async function (assert) {
            const mockRPC = (route) => {
                if (route === `/sign/refuse/${documentId}/${signRequestItemToken}`) {
                    assert.step("refuse-route-called");
                    return false;
                }
            };

            const env = await createEnvForDialog(mockRPC);
            patchWithCleanup(env.services.dialog, {
                add(component, props) {
                    if (component === AlertDialog) {
                        assert.step("alert-dialog");
                    }
                },
            });

            await mountSignRefusalDialog(env);

            await editInput(target, ".o_sign_refuse_confirm_message", "reason for refusal");
            assert.strictEqual(
                target.querySelector("button.refuse-button").disabled,
                false,
                "button should be enabled after textarea is filled"
            );
            await click(target.querySelector("button.refuse-button"));

            assert.verifySteps(["refuse-route-called", "alert-dialog"]);
        }
    );
});
