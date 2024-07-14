/** @odoo-module **/

import { click, getFixture, mount, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import {
    makeFakeUserService,
    makeFakeDialogService,
    makeFakeLocalizationService,
} from "@web/../tests/helpers/mock_services";
import { ItsmeDialog } from "@sign_itsme/dialogs/itsme_dialog";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { uiService } from "@web/core/ui/ui_service";

const serviceRegistry = registry.category("services");

let target;
const route = "/sign/sign/23/abc";
const params = { test: true };

QUnit.module("sign itsme dialog", function (hooks) {
    const mountItsmeDialog = async (mockRPC = {}, additionalProps = {}) => {
        const env = await makeTestEnv({ mockRPC });
        env.dialogData = {
            isActive: true,
            close: () => {},
        };

        await mount(ItsmeDialog, target, {
            props: {
                route,
                params,
                onSuccess: () => {},
                close: () => {},
                ...additionalProps,
            },
            env,
        });

        return env;
    };

    hooks.beforeEach(() => {
        target = getFixture();
        serviceRegistry.add("user", makeFakeUserService());
        serviceRegistry.add("dialog", makeFakeDialogService());
        serviceRegistry.add("localization", makeFakeLocalizationService());
        serviceRegistry.add("ui", uiService);
        serviceRegistry.add("hotkey", hotkeyService);
    });

    QUnit.test("itsme dialog is rendered correctly", async (assert) => {
        await mountItsmeDialog();

        assert.containsOnce(target, ".itsme_confirm", "should show itsme button");
        assert.containsOnce(target, ".itsme_cancel", "should show go back button");
    });

    QUnit.test("itsme dialog click itsme button should send request", async (assert) => {
        assert.expect(4);
        const mockRPC = (rte, args) => {
            if (rte === route) {
                assert.step("request-sent");
                assert.deepEqual(args, params, "params should be passed in request");
                return { success: true, authorization_url: false };
            }
        };

        const onSuccess = () => {
            assert.step("success");
        };

        await mountItsmeDialog(mockRPC, { onSuccess });

        await click(target, ".itsme_confirm");
        assert.verifySteps(["request-sent", "success"]);
    });

    QUnit.test("itsme dialog click itsme button should show error if rpc fails", async (assert) => {
        assert.expect(2);
        const errorMessage = "error_in_dialog";
        const mockRPC = (rte) => {
            if (rte === route) {
                return { success: false, message: errorMessage };
            }
        };

        const env = await mountItsmeDialog(mockRPC);

        patchWithCleanup(env.services.dialog, {
            add(component, props) {
                if (component === AlertDialog && props.body === errorMessage) {
                    assert.step("error-dialog");
                }
            },
        });

        await click(target, ".itsme_confirm");
        assert.verifySteps(["error-dialog"]);
    });
});
