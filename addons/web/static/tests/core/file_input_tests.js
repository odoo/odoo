/** @odoo-module **/

import { FileInput } from "@web/core/file_input/file_input";
import { registry } from "@web/core/registry";
import testUtils from "web.test_utils";
import { makeTestEnv } from "../helpers/mock_env";
import { getFixture, mount } from "../helpers/utils";

const serviceRegistry = registry.category("services");

let target;

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

    const fileInput = await mount(FileInput, target, {
        env,
        props: config.props,
    });
    return fileInput;
}

// -----------------------------------------------------------------------------
// Tests
// -----------------------------------------------------------------------------

QUnit.module("Components", ({ beforeEach }) => {
    beforeEach(() => {
        target = getFixture();
    });

    // This module cannot be tested as thoroughly as we want it to be:
    // browsers do not let scripts programmatically assign values to inputs
    // of type file
    QUnit.module("FileInput");

    QUnit.test("Upload a file: default props", async function (assert) {
        assert.expect(6);

        await createFileInput({
            mockPost: (route, params) => {
                assert.deepEqual(params, {
                    csrf_token: odoo.csrf_token,
                    ufile: [],
                });
                assert.step(route);
                return "[]";
            },
            props: {},
        });
        const input = target.querySelector("input");

        assert.strictEqual(
            target.querySelector(".o_file_input").innerText.trim().toUpperCase(),
            "CHOOSE FILE",
            "File input total text should match its given inner element's text"
        );
        assert.strictEqual(input.accept, "*", "Input should accept all files by default");

        await testUtils.dom.triggerEvent(input, "change");

        assert.notOk(input.multiple, "'multiple' attribute should not be set");
        assert.verifySteps(["/web/binary/upload"]);
    });

    QUnit.test("Upload a file: custom attachment", async function (assert) {
        assert.expect(6);

        await createFileInput({
            props: {
                accepted_file_extensions: ".png",
                action: "/web/binary/upload_attachment",
                id: 5,
                model: "res.model",
                multi_upload: true,
                onUpload(files) {
                    assert.strictEqual(
                        files.length,
                        0,
                        "'files' property should be an empty array"
                    );
                },
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
        });
        const input = target.querySelector("input");

        assert.strictEqual(input.accept, ".png", "Input should now only accept pngs");

        await testUtils.dom.triggerEvent(input, "change");

        assert.ok(input.multiple, "'multiple' attribute should be set");
        assert.verifySteps(["/web/binary/upload_attachment"]);
    });
});
