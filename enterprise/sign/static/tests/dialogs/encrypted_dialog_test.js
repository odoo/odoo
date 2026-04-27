/** @odoo-module **/

import { click, getFixture, mount, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import {
    makeFakeDialogService,
    makeFakeLocalizationService,
} from "@web/../tests/helpers/mock_services";
import { EncryptedDialog } from "@sign/dialogs/dialogs";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { uiService } from "@web/core/ui/ui_service";

const serviceRegistry = registry.category("services");
const documentId = 23;
let target;

QUnit.module("encrypted dialog", function (hooks) {
    const createEnvForDialog = async (mockRPC = {}) => {
        const env = await makeTestEnv({ mockRPC });
        env.dialogData = {
            isActive: true,
            close: () => {},
        };
        return env;
    };
    const mountEncryptedDialog = async (env) => {
        if (!env) {
            env = await createEnvForDialog();
        }
        await mount(EncryptedDialog, target, {
            props: {
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
        const signInfo = {
            documentId,
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

    QUnit.test("encrypted dialog is rendered correctly", async (assert) => {
        await mountEncryptedDialog();

        assert.containsOnce(target, "input[type='password']", "should render password input");
        assert.containsOnce(
            target,
            "button.o_sign_validate_encrypted",
            "should render generate PDF button"
        );
    });

    QUnit.test("encrypted dialog should validate input", async (assert) => {
        await mountEncryptedDialog();

        assert.strictEqual(
            target.querySelector("input[type='password']").classList.contains("is-invalid"),
            false,
            "input should not have is-invalid class at start"
        );
        await click(target, "button.o_sign_validate_encrypted");
        assert.strictEqual(
            target.querySelector("input[type='password']").classList.contains("is-invalid"),
            true,
            "should add is-invalid class on the input"
        );
    });

    QUnit.test("encrypted dialog should call password route", async (assert) => {
        const ultraSafePassword = "tryme";
        const mockRPC = (route, args) => {
            if (route === `/sign/password/${documentId}` && args.password === ultraSafePassword) {
                assert.step("password-validated");
                return true;
            }
        };
        await mountEncryptedDialog(await createEnvForDialog(mockRPC));

        target.querySelector("input[type='password']").value = ultraSafePassword;
        await click(target, "button.o_sign_validate_encrypted");

        assert.verifySteps(["password-validated"]);
    });

    QUnit.test("encrypted dialog should show error dialog if password is wrong", async (assert) => {
        const ultraSafePassword = "tryme";
        const mockRPC = (route, args) => {
            if (route === `/sign/password/${documentId}` && args.password !== ultraSafePassword) {
                assert.step("password-wrong");
                return false;
            }
        };

        const env = await createEnvForDialog(mockRPC);

        patchWithCleanup(env.services.dialog, {
            add(component, props) {
                if (component === AlertDialog) {
                    assert.step("error-dialog");
                }
            },
        });

        await mountEncryptedDialog(env);
        target.querySelector("input[type='password']").value = "abc";
        await click(target, "button.o_sign_validate_encrypted");

        assert.verifySteps(["password-wrong", "error-dialog"]);
    });
});
