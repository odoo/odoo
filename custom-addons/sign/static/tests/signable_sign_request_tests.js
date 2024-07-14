/** @odoo-module **/

import { getFixture, nextTick } from "@web/../tests/helpers/utils";
import { doAction } from "@web/../tests/webclient/helpers";
import { createDocumentWebClient, actionId } from "./action_utils";
import { signInfoService } from "@sign/services/sign_info_service";
import { registry } from "@web/core/registry";

let serverData;
let target;
let config;

QUnit.module("signable_document_backend_tests", ({ beforeEach }) => {
    beforeEach(() => {
        const data = {
            partner: {
                fields: {
                    display_name: { string: "Displayed name", type: "char" },
                    template_id: {
                        string: "Template",
                        type: "many2one",
                        relation: "sign.template",
                    },
                },
                records: [
                    {
                        id: 1,
                        display_name: "some record",
                        template_id: 1,
                    },
                ],
            },
            "sign.template": {
                fields: {
                    display_name: { string: "Template Name", type: "char" },
                },
                records: [
                    {
                        id: 1,
                        display_name: "some template",
                    },
                ],
            },
        };
        serverData = { models: data };
        target = getFixture();
        config = {
            tag: "sign.SignableDocument",
        };
        registry.category("services").add("signInfo", signInfoService);
    });

    QUnit.test("simple rendering", async (assert) => {
        assert.expect(5);
        const getDataFromHTML = () => {
            assert.step("getDataFromHTML");
        };
        config.getDataFromHTML = getDataFromHTML;

        const webClient = await createDocumentWebClient(config, serverData);
        await doAction(webClient, actionId);
        await nextTick();

        assert.verifySteps(["getDataFromHTML"]);

        assert.strictEqual(
            target.querySelector(".o_sign_document").innerText.trim(),
            "def",
            "should display text from server"
        );

        assert.containsNone(
            target,
            ".d-xl-inline-flex .o_sign_edit_button",
            "should show edit while signing button"
        );
        assert.containsNone(
            target,
            ".d-xl-inline-flex .o_sign_refuse_document_button",
            "should show refuse button"
        );
    });

    QUnit.test("rendering with allow edit to sign", async (assert) => {
        config.actionContext = { template_editable: true };
        const webClient = await createDocumentWebClient(config, serverData);

        await doAction(webClient, actionId);

        assert.containsOnce(
            target,
            ".d-xl-inline-flex .o_sign_edit_button",
            "should show edit while signing button"
        );
    });

    QUnit.test("rendering with allow refusal", async (assert) => {
        const mockRPC = (route) => {
            if (route === "/sign/get_document/5/abc") {
                return Promise.resolve({
                    html: `
                    <span>
                        def
                        <div class='o_sign_cp_pager'></div>
                    </span>
                    `,
                    context: { refusal_allowed: true },
                });
            }
        };

        config.mockRPC = mockRPC;
        const webClient = await createDocumentWebClient(config, serverData);

        await doAction(webClient, actionId);

        assert.containsOnce(
            target,
            ".d-xl-inline-flex .o_sign_refuse_document_button",
            "should show refuse button"
        );
    });
});
