/** @odoo-module **/

import { registry } from "@web/core/registry";
import { setupViewRegistries } from "@web/../tests/views/helpers";
import { makeFakeLocalizationService } from "../helpers/mock_services";
import { dialogService } from "@web/core/dialog/dialog_service";
import { popoverService } from "@web/core/popover/popover_service";

const serviceRegistry = registry.category("services");

QUnit.module("Views", (hooks) => {
    QUnit.module("Helpers tests");

    QUnit.test("setupViewRegistries overwrite services", async function (assert) {
        serviceRegistry.add("localization", makeFakeLocalizationService(), { force: true });
        serviceRegistry.add("dialog", dialogService, { force: true });
        serviceRegistry.add("popover", popoverService, { force: true });
        setupViewRegistries(); // crash if does not overwrite (force)
        assert.ok(true, "setupViewRegistries overwrite services");
    });
});
