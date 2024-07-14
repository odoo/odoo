/** @odoo-module */

import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { registry } from "@web/core/registry";
import { ormService } from "@web/core/orm_service";

import { RecordFileStore } from "@spreadsheet_edition/bundle/image/record_file_store";

QUnit.module(
    "Record file store",
    {
        beforeEach() {
            registry.category("services").add("orm", ormService);
        },
    },
    async () => {
        QUnit.test("upload image", async (assert) => {
            const fakeHTTPService = {
                start() {
                    return {
                        post: (route, params) => {
                            assert.step("image uploaded");
                            assert.strictEqual(params.model, "res.partner");
                            assert.strictEqual(params.id, 1);
                            assert.strictEqual(route, "/web/binary/upload_attachment");
                            return JSON.stringify([
                                {
                                    id: 10,
                                    name: params.ufile[0].name,
                                    mimetype: "image/png",
                                },
                            ]);
                        },
                    };
                },
            };
            const fakeORMService = {
                start() {
                    return {
                        call: (model, method, args) => {
                            assert.step("access token generated");
                            assert.strictEqual(model, "ir.attachment");
                            assert.strictEqual(method, "generate_access_token");
                            assert.deepEqual(args, [10]);
                            return ["the-image-access-token"];
                        },
                    };
                },
            };
            registry.category("services").add("http", fakeHTTPService);
            registry.category("services").add("orm", fakeORMService, { force: true });
            const env = await makeTestEnv();
            const fileStore = new RecordFileStore(
                "res.partner",
                1,
                env.services.http,
                env.services.orm
            );
            const path = await fileStore.upload(
                new File(["image"], "image_name.png", { type: "image/*" })
            );
            assert.strictEqual(path, "/web/image/10?access_token=the-image-access-token");
            assert.verifySteps(["image uploaded", "access token generated"]);
        });

        QUnit.test("delete image", async (assert) => {
            const env = await makeTestEnv({
                mockRPC: (route, args) => {
                    if (args.method === "unlink") {
                        const ids = args.args[0];
                        assert.step(`image ${ids} deleted`);
                        assert.strictEqual(args.model, "ir.attachment");
                        return true;
                    }
                },
            });
            const fileStore = new RecordFileStore(
                "res.partner",
                1,
                env.services.http,
                env.services.orm
            );
            await fileStore.delete("/web/image/10");
            await fileStore.delete("/web/image/11?access_token=the-image-access-token");
            assert.verifySteps(["image 10 deleted", "image 11 deleted"]);
        });

        QUnit.test("delete file with path without attachment id", async (assert) => {
            const env = await makeTestEnv({
                mockRPC: (route, args) => {
                    if (args.method === "unlink") {
                        throw new Error("unlink should not be called");
                    }
                },
            });
            const fileStore = new RecordFileStore(
                "res.partner",
                1,
                env.services.http,
                env.services.orm
            );
            assert.rejects(fileStore.delete("/web/image/path/without/id"));
        });
    }
);
