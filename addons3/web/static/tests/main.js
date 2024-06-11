/** @odoo-module **/

import { setupQUnit } from "./qunit";
import { setupTests } from "./setup";

(async () => {
    setupQUnit();
    await setupTests();
    QUnit.start();
})();
