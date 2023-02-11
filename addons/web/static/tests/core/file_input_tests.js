/** @odoo-module **/

import { FileInput } from "@web/core/file_input/file_input";
import { registry } from "@web/core/registry";
import testUtils from "web.test_utils";
import { makeTestEnv } from "../helpers/mock_env";
import { getFixture } from "../helpers/utils";

const { mount } = owl;
const serviceRegistry = registry.category("services");

// -----------------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------------

async function createFileInput(config) {
    const fakeHTTPService = {
        start() {
            return {
                post: config.mockPost || (() => {}),
            };
        },
    };
    serviceRegistry.add("http", fakeHTTPService);

    const env = await makeTestEnv();
    const target = getFixture();
    if (config.onUploaded) {
        target.addEventListener("uploaded", config.onUploaded);
    }

    const fileInput = await mount(FileInput, {
        env,
        props: config.props,
        target,
    });
    return fileInput;
}

// -----------------------------------------------------------------------------
// Tests
// -----------------------------------------------------------------------------

QUnit.module("Components", () => {
    // This module cannot be tested as thoroughly as we want it to be:
    // browsers do not let scripts programmatically assign values to inputs
    // of type file
    QUnit.module("FileInput");

    QUnit.test("Upload a file: default props", async function (assert) {
        assert.expect(6);

        const fileInput = await createFileInput({
            mockPost: (route, params) => {
                assert.deepEqual(params, {
                    csrf_token: odoo.csrf_token,
                    ufile: [],
                });
                assert.step(route);
                return "[]";
            },
        });
        const input = fileInput.el.querySelector("input");

        assert.strictEqual(
            fileInput.el.innerText.trim().toUpperCase(),
            "CHOOSE FILE",
            "File input total text should match its given inner element's text"
        );
        assert.strictEqual(input.accept, "*", "Input should accept all files by default");

        await testUtils.dom.triggerEvent(input, "change");

        assert.notOk(input.multiple, "'multiple' attribute should not be set");
        assert.verifySteps(["/web/binary/upload"]);

        fileInput.destroy();
    });

    QUnit.test("Upload a file: custom attachment", async function (assert) {
        assert.expect(6);

        const fileInput = await createFileInput({
            props: {
                accepted_file_extensions: ".png",
                action: "/web/binary/upload_attachment",
                id: 5,
                model: "res.model",
                multi_upload: true,
            },
            mockPost: (route, params) => {
                assert.deepEqual(params, {
                    id: 5,
                    model: "res.model",
                    csrf_token: odoo.csrf_token,
                    ufile: [],
                });
                assert.step(route);
                return "[]";
            },
            onUploaded(ev) {
                assert.strictEqual(
                    ev.detail.files.length,
                    0,
                    "'files' property should be an empty array"
                );
            },
        });
        const input = fileInput.el.querySelector("input");

        assert.strictEqual(input.accept, ".png", "Input should now only accept pngs");

        await testUtils.dom.triggerEvent(input, "change");

        assert.ok(input.multiple, "'multiple' attribute should be set");
        assert.verifySteps(["/web/binary/upload_attachment"]);

        fileInput.destroy();
    });
});
