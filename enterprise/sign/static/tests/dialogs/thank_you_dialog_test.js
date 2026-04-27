/** @odoo-module **/

import { getFixture, mount, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import {
    makeFakeDialogService,
    makeFakeLocalizationService,
} from "@web/../tests/helpers/mock_services";
import { ThankYouDialog } from "@sign/dialogs/dialogs";
import { registry } from "@web/core/registry";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { uiService } from "@web/core/ui/ui_service";
import { user } from "@web/core/user";

const serviceRegistry = registry.category("services");

let target;

QUnit.module("thank you dialog", (hooks) => {
    const createEnv = async (mockRPC) => {
        const env = await makeTestEnv({ mockRPC });
        env.dialogData = {
            isActive: true,
            close: () => {},
        };
        return env;
    };

    const mountThankYouDialog = async (env, additionalProps = {}) => {
        return mount(ThankYouDialog, target, {
            props: {
                message: "bla",
                subtitle: "aha",
                close: () => {},
                ...additionalProps,
            },
            env,
        });
    };

    hooks.beforeEach(async () => {
        target = getFixture();
        serviceRegistry.add("dialog", makeFakeDialogService());
        serviceRegistry.add("localization", makeFakeLocalizationService());
        serviceRegistry.add("ui", uiService);
        serviceRegistry.add("hotkey", hotkeyService);
        const signInfo = {
            documentId: 23,
            signRequestToken: "abc",
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

    QUnit.test("Thank you dialog is correctly rendered", async (assert) => {
        const mockRPC = (route) => {
            if (route === "/sign/encrypted/23") {
                return false;
            } else if (route === "/sign/sign_request_state/23/abc") {
                return "draft";
            } else if (route === "/sign/sign_request_items") {
                return [];
            } else if (route === "/web/dataset/call_kw/sign.request/get_close_values") {
                return {
                    label: "Close",
                    action: {
                        type: "ir.actions.act_window",
                        res_model: "sign_request",
                        views: [[false, "kanban"]],
                    },
                };
            }
        };

        await mountThankYouDialog(await createEnv(mockRPC));

        assert.strictEqual(target.querySelector(".modal-title").textContent.trim(), "It's signed!");
        assert.strictEqual(
            target.querySelector("#thank-you-message").textContent,
            "bla",
            "Should render message"
        );
        assert.strictEqual(
            target.querySelector("#thank-you-subtitle").textContent,
            "aha",
            "Should render subtitle"
        );
        assert.strictEqual(
            target.querySelector(".o_sign_thankyou_close_button").textContent,
            "Close",
            "Should render close button"
        );
    });

    QUnit.test("suggest signup is shown", async (assert) => {
        const mockRPC = (route) => {
            if (route === "/sign/encrypted/23") {
                return false;
            } else if (route === "/sign/sign_request_state/23/abc") {
                return "draft";
            } else if (route === "/sign/sign_request_items") {
                return [];
            } else if (route === "/web/dataset/call_kw/sign.request/get_close_values") {
                return {
                    label: "Close",
                    action: {
                        type: "ir.actions.act_window",
                        res_model: "sign_request",
                        views: [[false, "kanban"]],
                    },
                };
            }
        };

        const env = await createEnv(mockRPC);

        patchWithCleanup(user, { userId: false });

        await mountThankYouDialog(env);

        assert.strictEqual(
            target.querySelector("#thank-you-message").textContent,
            "bla",
            "Should render message"
        );
        assert.containsOnce(
            target,
            "a:contains('Odoo Sign')",
            "Should render sign up link"
        );
    });

    QUnit.test("download button is shown when document is completed", async (assert) => {
        const mockRPC = (route) => {
            if (route === "/sign/encrypted/23") {
                return false;
            } else if (route === "/sign/sign_request_state/23/abc") {
                return "signed";
            } else if (route === "/sign/sign_request_items") {
                return [];
            } else if (route === "/web/dataset/call_kw/sign.request/get_close_values") {
                return {
                    label: "Close",
                    action: {
                        type: "ir.actions.act_window",
                        res_model: "sign_request",
                        views: [[false, "kanban"]],
                    },
                };
            }
        };

        await mountThankYouDialog(await createEnv(mockRPC));

        assert.containsOnce(
            target,
            "button:contains('Download')",
            "Should render download document button"
        );
    });

    QUnit.test("redirect button works", async (assert) => {
        const mockRPC = (route) => {
            if (route === "/sign/encrypted/23") {
                return false;
            } else if (route === "/sign/sign_request_state/23/abc") {
                return "signed";
            } else if (route === "/sign/sign_request_items") {
                return [];
            } else if (route === "/web/dataset/call_kw/sign.request/get_close_values") {
                return {
                    label: "Close",
                    action: {
                        type: "ir.actions.act_window",
                        res_model: "sign_request",
                        views: [[false, "kanban"]],
                    },
                };
            }
        };

        await mountThankYouDialog(await createEnv(mockRPC), {
            redirectURL: "https://shorturl.at/jnxMP",
            redirectURLText: "Redirect Button",
        });

        assert.strictEqual(
            target.querySelector(".o_sign_thankyou_redirect_button").textContent,
            "Redirect Button",
            "Should render redirect button when redirectURL is passed as props"
        );
        assert.containsOnce(
            target,
            "button:contains('Download')",
            "Should render download document button"
        );
    });
});
