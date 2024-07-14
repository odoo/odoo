/** @odoo-module **/

import { click, getFixture, mount, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import {
    makeFakeUserService,
    makeFakeDialogService,
    makeFakeLocalizationService,
} from "@web/../tests/helpers/mock_services";
import { ThankYouDialog } from "@sign/dialogs/dialogs";
import { registry } from "@web/core/registry";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { uiService } from "@web/core/ui/ui_service";
import { session } from "@web/session";

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
        serviceRegistry.add("user", makeFakeUserService());
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
            }
        };

        await mountThankYouDialog(await createEnv(mockRPC));

        assert.strictEqual(
            target.querySelector(".modal-title").textContent.trim(),
            "Thank you! Your signature has been submitted."
        );
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
            target.querySelector("button.btn-primary").textContent,
            "Close",
            "Should render close button"
        );
    });

    QUnit.test("Thank you dialog shows nextDocuments", async (assert) => {
        const nextDocuments = [
            {
                id: 1,
                name: "Test",
                date: "2022-12-12",
                user: 1,
                token: "123abc",
                requestId: 2,
            },
            {
                id: 2,
                name: "Test 2",
                date: "2022-12-12",
                user: 1,
                token: "abc123",
                requestId: 3,
            },
        ];
        const mockRPC = (route) => {
            if (route === "/sign/encrypted/23") {
                return false;
            } else if (route === "/sign/sign_request_state/23/abc") {
                return "draft";
            } else if (route === "/sign/sign_request_items") {
                return nextDocuments;
            } else if (route.includes("/sign/ignore_sign_request_item")) {
                return true;
            }
        };

        patchWithCleanup(ThankYouDialog.prototype, {
            goToDocument: (id, token) => {
                if (id === nextDocuments[0].requestId && token === nextDocuments[0].token) {
                    assert.step("sign-first-document");
                } else if (id === nextDocuments[1].requestId && token === nextDocuments[1].token) {
                    assert.step("sign-second-document");
                }
            },
        });

        await mountThankYouDialog(await createEnv(mockRPC));

        assert.containsN(target, ".next-document", 2, "Should render two next documents to sign");
        const nextDocumentNames = Array.from(target.querySelectorAll(".next-document strong")).map(
            (item) => item.textContent
        );
        assert.deepEqual(
            nextDocumentNames,
            ["Test", "Test 2"],
            "Should render the names of the next documents"
        );

        assert.containsOnce(
            target,
            "button:contains('Sign Next Document')",
            "Should render sign next document button"
        );
        await click(target.querySelector(".next-document .o_thankyou_next_sign"));

        // ignore first document, see that class changes
        await click(target.querySelector(".next-document .o_thankyou_next_ignore"));

        assert.containsOnce(
            target,
            ".next-document.text-muted",
            "Should add muted class after a document is ignored"
        );

        const signNextDocumentButton = Array.from(target.querySelectorAll("button")).find(
            (button) => button.textContent === "Sign Next Document"
        );

        await click(signNextDocumentButton);
        assert.verifySteps(["sign-first-document", "sign-second-document"]);

        assert.equal(
            signNextDocumentButton.disabled,
            false,
            "Sign next document button should be enabled at first"
        );
        await click(
            target.querySelector(".next-document:not(.text-muted) .o_thankyou_next_ignore")
        );
        assert.containsN(target, ".next-document.text-muted", 2, "All documents should be muted");
        assert.equal(
            signNextDocumentButton.disabled,
            true,
            "Sign next document should be disabled as all documents are ignored"
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
            }
        };

        const env = await createEnv(mockRPC);

        patchWithCleanup(session, {user_id: false});

        await mountThankYouDialog(env);

        assert.strictEqual(
            target.querySelector("#thank-you-message").textContent,
            "bla You can safely close this window.",
            "Should render message"
        );
        assert.containsOnce(
            target,
            "button:contains('Sign Up for free')",
            "Should render sign up button"
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
            }
        };

        await mountThankYouDialog(await createEnv(mockRPC));

        assert.containsOnce(
            target,
            "button:contains('Download Document')",
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
            }
        };

        await mountThankYouDialog(await createEnv(mockRPC), {
            redirectURL: "https://shorturl.at/jnxMP",
            redirectURLText: "Redirect Button",
        });

        assert.strictEqual(
            target.querySelector("button.btn-primary").textContent,
            "Redirect Button",
            "Should render redirect button when redirectURL is passed as props"
        );
        assert.containsOnce(
            target,
            "button:contains('Download Document')",
            "Should render download document button"
        );
    });
});
