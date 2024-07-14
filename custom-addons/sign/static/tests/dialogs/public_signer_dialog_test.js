/** @odoo-module **/

import { click, getFixture, mount, editInput } from "@web/../tests/helpers/utils";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import {
    makeFakeUserService,
    makeFakeDialogService,
    makeFakeLocalizationService,
} from "@web/../tests/helpers/mock_services";
import { PublicSignerDialog } from "@sign/dialogs/dialogs";
import { registry } from "@web/core/registry";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { uiService } from "@web/core/ui/ui_service";

const serviceRegistry = registry.category("services");
const fakeName = "Pericles";
const fakeMail = "pericles@test.com";
const documentId = 23;
const signRequestToken = "abc";

let target;

QUnit.module("public signer dialog", function (hooks) {
    const mountPublicSignerDialog = async (mockRPC = {}, additionalProps = {}) => {
        const env = await makeTestEnv({ mockRPC });
        env.dialogData = {
            isActive: true,
            close: () => {},
        };

        await mount(PublicSignerDialog, target, {
            props: {
                name: fakeName,
                mail: fakeMail,
                postValidation: () => {},
                close: () => {},
                ...additionalProps,
            },
            env,
        });
    };

    hooks.beforeEach(() => {
        target = getFixture();
        serviceRegistry.add("user", makeFakeUserService());
        serviceRegistry.add("dialog", makeFakeDialogService());
        serviceRegistry.add("localization", makeFakeLocalizationService());
        serviceRegistry.add("ui", uiService);
        serviceRegistry.add("hotkey", hotkeyService);
        const signInfo = {
            documentId,
            signRequestToken,
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

    QUnit.test("public signer dialog is rendered correctly", async (assert) => {
        await mountPublicSignerDialog();

        assert.containsOnce(
            target,
            "#o_sign_public_signer_name_input",
            "should contain name input"
        );
        assert.strictEqual(
            target.querySelector("#o_sign_public_signer_name_input").value,
            fakeName,
            "name should be prefilled"
        );
        assert.containsOnce(
            target,
            "#o_sign_public_signer_mail_input",
            "should contain email input"
        );
        assert.strictEqual(
            target.querySelector("#o_sign_public_signer_mail_input").value,
            fakeMail,
            "mail should be prefilled"
        );
        assert.containsOnce(
            target,
            "button.btn-primary:contains('Validate & Send')",
            "should show validate button"
        );
    });

    QUnit.test("public signer dialog correctly submits data", async (assert) => {
        assert.expect(5);
        const mockAccessToken = "zyx";
        const mockRequestId = 11;
        const mockRequestToken = "def";
        const mockRPC = (route, args) => {
            if (
                route === `/sign/send_public/${documentId}/${signRequestToken}` &&
                args.name === fakeName &&
                args.mail === fakeMail
            ) {
                assert.step("sign-public-success");
                return {
                    requestID: mockRequestId,
                    requestToken: mockRequestToken,
                    accessToken: mockAccessToken,
                };
            }
        };

        await mountPublicSignerDialog(mockRPC, {
            postValidation: (requestId, requestToken, accessToken) => {
                assert.strictEqual(requestId, mockRequestId);
                assert.strictEqual(requestToken, mockRequestToken);
                assert.strictEqual(accessToken, mockAccessToken);
            },
        });
        await click(target, ".btn-primary");
        assert.verifySteps(["sign-public-success"]);
    });

    QUnit.test("public signer dialog inputs validation", async (assert) => {
        await mountPublicSignerDialog(
            {},
            {
                name: "",
            }
        );

        const nameInput = target.querySelector("#o_sign_public_signer_name_input");
        const mailInput = target.querySelector("#o_sign_public_signer_mail_input");

        assert.strictEqual(nameInput.classList.contains("is-invalid"), false);
        await click(target, ".btn-primary");
        assert.strictEqual(nameInput.classList.contains("is-invalid"), true);

        assert.strictEqual(mailInput.classList.contains("is-invalid"), false);
        editInput(target, "#o_sign_public_signer_mail_input", "abc");
        await click(target, ".btn-primary");
        assert.strictEqual(mailInput.classList.contains("is-invalid"), true);

        editInput(target, "#o_sign_public_signer_mail_input", fakeMail);
        await click(target, ".btn-primary");
        assert.strictEqual(nameInput.classList.contains("is-invalid"), true);
        assert.strictEqual(mailInput.classList.contains("is-invalid"), false);
    });
});
