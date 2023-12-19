/** @odoo-module alias=@web/../tests/main default=false */

import { setupQUnit } from "./qunit";
import { setupTests } from "./setup";

(async () => {
    setupQUnit();
    await setupTests();
    QUnit.start();
})();
