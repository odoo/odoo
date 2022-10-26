/** @odoo-module */

import { nextTick } from "@web/../tests/helpers/utils";
import { MetadataRepository } from "@spreadsheet/data_sources/metadata_repository";

QUnit.module("spreadsheet > Metadata Repository", {}, () => {
    QUnit.test("Fields_get are only loaded once", async function (assert) {
        assert.expect(6);

        const orm = {
            silent: {
                call: async (model, method) => {
                    assert.step(`${method}-${model}`);
                    return model;
                },
            },
        };

        const metadataRepository = new MetadataRepository(orm);

        const first = await metadataRepository.fieldsGet("A");
        const second = await metadataRepository.fieldsGet("A");
        const third = await metadataRepository.fieldsGet("B");

        assert.strictEqual(first, "A");
        assert.strictEqual(second, "A");
        assert.strictEqual(third, "B");

        assert.verifySteps(["fields_get-A", "fields_get-B"]);
    });

    QUnit.test("display_name_for on ir.model are only loaded once", async function (assert) {
        assert.expect(6);

        const orm = {
            silent: {
                call: async (model, method, args) => {
                    if (method === "display_name_for" && model === "ir.model") {
                        const [modelName] = args[0];
                        assert.step(`${modelName}`);
                        return [{ display_name: modelName, model: modelName }];
                    }
                },
            },
        };

        const metadataRepository = new MetadataRepository(orm);

        const first = await metadataRepository.modelDisplayName("A");
        const second = await metadataRepository.modelDisplayName("A");
        const third = await metadataRepository.modelDisplayName("B");

        assert.strictEqual(first, "A");
        assert.strictEqual(second, "A");
        assert.strictEqual(third, "B");

        assert.verifySteps(["A", "B"]);
    });

    QUnit.test("Register label correctly memorize labels", function (assert) {
        assert.expect(2);

        const metadataRepository = new MetadataRepository({ silent: {} });

        assert.strictEqual(metadataRepository.getLabel("model", "field", "value"), undefined);
        const label = "label";
        metadataRepository.registerLabel("model", "field", "value", label);
        assert.strictEqual(metadataRepository.getLabel("model", "field", "value"), label);
    });

    QUnit.test("Name_get are collected and executed once by clock", async function (assert) {
        const orm = {
            silent: {
                call: async (model, method, args) => {
                    const ids = args[0];
                    assert.step(`${method}-${model}-[${ids.join(",")}]`);
                    return ids.map((id) => [id, id.toString()]);
                },
            },
        };

        const metadataRepository = new MetadataRepository(orm);
        metadataRepository.addEventListener("labels-fetched", () => {
            assert.step("labels-fetched");
        });

        assert.throws(() => metadataRepository.getRecordDisplayName("A", 1), /Data is loading/);
        assert.throws(() => metadataRepository.getRecordDisplayName("A", 1), /Data is loading/);
        assert.throws(() => metadataRepository.getRecordDisplayName("A", 2), /Data is loading/);
        assert.throws(() => metadataRepository.getRecordDisplayName("B", 1), /Data is loading/);
        assert.verifySteps([]);

        await nextTick();
        assert.verifySteps([
            "name_get-A-[1,2]",
            "name_get-B-[1]",
            "labels-fetched",
            "labels-fetched",
        ]);

        assert.strictEqual(metadataRepository.getRecordDisplayName("A", 1), "1");
        assert.strictEqual(metadataRepository.getRecordDisplayName("A", 2), "2");
        assert.strictEqual(metadataRepository.getRecordDisplayName("B", 1), "1");
    });

    QUnit.test("Name_get to fetch are cleared after being fetched", async function (assert) {
        const orm = {
            silent: {
                call: async (model, method, args) => {
                    const ids = args[0];
                    assert.step(`${method}-${model}-[${ids.join(",")}]`);
                    return ids.map((id) => [id, id.toString()]);
                },
            },
        };

        const metadataRepository = new MetadataRepository(orm);

        assert.throws(() => metadataRepository.getRecordDisplayName("A", 1));
        assert.verifySteps([]);

        await nextTick();
        assert.verifySteps(["name_get-A-[1]"]);

        assert.throws(() => metadataRepository.getRecordDisplayName("A", 2));
        await nextTick();
        assert.verifySteps(["name_get-A-[2]"]);
    });

    QUnit.test(
        "Name_get will retry with one id by request in case of failure",
        async function (assert) {
            const orm = {
                silent: {
                    call: async (model, method, args) => {
                        const ids = args[0];
                        assert.step(`${method}-${model}-[${ids.join(",")}]`);
                        if (model === "B" && ids.includes(1)) {
                            throw new Error("Missing");
                        }
                        return ids.map((id) => [id, id.toString()]);
                    },
                },
            };

            const metadataRepository = new MetadataRepository(orm);

            assert.throws(() => metadataRepository.getRecordDisplayName("A", 1), /Data is loading/);
            assert.throws(() => metadataRepository.getRecordDisplayName("B", 1), /Data is loading/);
            assert.throws(() => metadataRepository.getRecordDisplayName("B", 2), /Data is loading/);
            assert.verifySteps([]);

            await nextTick();
            assert.verifySteps([
                "name_get-A-[1]",
                "name_get-B-[1,2]",
                "name_get-B-[1]",
                "name_get-B-[2]",
            ]);

            assert.strictEqual(metadataRepository.getRecordDisplayName("A", 1), "1");
            assert.throws(
                () => metadataRepository.getRecordDisplayName("B", 1),
                /Unable to fetch the label of 1 of model B/
            );
            assert.strictEqual(metadataRepository.getRecordDisplayName("B", 2), "2");
        }
    );
});
