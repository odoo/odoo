/** @odoo-module **/
import { setupTests } from "./helpers/index";

(async () => {
  await setupTests();
  QUnit.start();
})();
