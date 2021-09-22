/** @odoo-module **/

import { setupTests } from "./setup";

(async () => {
    await setupTests();
    QUnit.start();
})();
