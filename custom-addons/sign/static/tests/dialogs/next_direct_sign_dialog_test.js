/** @odoo-module **/

import { click, getFixture, mount, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import {
    makeFakeUserService,
    makeFakeDialogService,
    makeFakeLocalizationService,
} from "@web/../tests/helpers/mock_services";
import { NextDirectSignDialog } from "@sign/dialogs/dialogs";
import { registry } from "@web/core/registry";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { uiService } from "@web/core/ui/ui_service";

const serviceRegistry = registry.category("services");

const documentId = 23;
const signRequestState = "sent";
const tokenList = ["abc", "def"];
const nameList = ["Brandon", "Coleen"];
const fakeActionService = {
    name: "action",
    start() {
        return {
            doAction(actionId) {
                return Promise.resolve(true);
            },
            loadState(state, options) {
                return Promise.resolve(true);
            },
        };
    },
};

let target;
QUnit.module("next direct sign dialog", function (hooks) {
    const mountNextDirectSignDialog = async () => {
        const env = await makeTestEnv();
        env.dialogData = {
            isActive: true,
            close: () => {},
        };

        await mount(NextDirectSignDialog, target, {
            props: {
                close: () => {},
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
        serviceRegistry.add("action", fakeActionService);
        const signInfo = {
            documentId,
            createUid: 7,
            signRequestState,
            tokenList,
            nameList,
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

    QUnit.test("next direct sign dialog should render", async function (assert) {
        await mountNextDirectSignDialog();
        assert.containsOnce(
            target,
            ".o_nextdirectsign_message",
            "should render next direct sign message"
        );
        assert.strictEqual(
            target.querySelector(".o_nextdirectsign_message p").textContent,
            "Your signature has been saved. Next signatory is Brandon",
            "next signatory should be brandon"
        );
        assert.strictEqual(
            target.querySelector(".btn-primary").textContent,
            "Next signatory (Brandon)"
        );
    });

    QUnit.test("next direct sign dialog should go to next document", async function (assert) {
        assert.expect(2);
        const env = await mountNextDirectSignDialog();
        patchWithCleanup(env.services.action, {
            doAction(action, params) {
                assert.strictEqual(action.tag, "sign.SignableDocument");
                const expected = {
                    id: documentId,
                    create_uid: env.services.user.userId,
                    state: signRequestState,
                    token: "abc",
                    token_list: ["def"],
                    name_list: ["Coleen"],
                };
                assert.deepEqual(
                    params.additionalContext,
                    expected,
                    "action should be called with correct params"
                );
            },
        });

        await click(target, ".btn-primary");
    });
});
