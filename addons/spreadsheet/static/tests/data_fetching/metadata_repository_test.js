/** @odoo-module */

import { registry } from "@web/core/registry";
import { ormService } from "@web/core/orm_service";
import { nameService } from "@web/core/name_service";
import { MetadataRepository } from "@spreadsheet/data_sources/metadata_repository";

function beforeEach() {
    registry
        .category("services")
        .add("name", nameService, { force: true })
        .add("orm", ormService, { force: true });
}

QUnit.module("spreadsheet > Metadata Repository", { beforeEach }, () => {
    QUnit.test("Register label correctly memorize labels", async function (assert) {
        assert.expect(2);
        const metadataRepository = new MetadataRepository();

        assert.strictEqual(metadataRepository.getLabel("model", "field", "value"), undefined);
        const label = "label";
        metadataRepository.registerLabel("model", "field", "value", label);
        assert.strictEqual(metadataRepository.getLabel("model", "field", "value"), label);
    });
});
