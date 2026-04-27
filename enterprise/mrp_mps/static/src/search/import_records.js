/** @odoo-module **/

import { ImportRecords } from "@base_import/import_records/import_records";
import { registry } from "@web/core/registry";

const favoriteMenuRegistry = registry.category("favoriteMenu");
const mpsImportRecordsItem = {
    Component: ImportRecords,
    groupNumber: 4,
    isDisplayed: ({ config }) =>
        config.mpsImportRecords
};
favoriteMenuRegistry.add("mps-import-records-menu", mpsImportRecordsItem, { sequence: 1 });
