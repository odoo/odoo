import { isHootReady, start } from "@odoo/hoot";

import "./core/expect.test.js";
import "./core/runner.test.js";
import "./core/suite.test.js";
import "./core/test.test.js";
import "./hoot-dom/dom.test.js";
import "./hoot-dom/events.test.js";
import "./hoot-dom/time.test.js";
import "./hoot_utils.test.js";
import "./mock/navigator.test.js";
import "./mock/network.test.js";
import "./mock/window.test.js";
import "./ui/hoot_technical_value.test.js";
import "./ui/hoot_test_result.test.js";

isHootReady.then(start);
