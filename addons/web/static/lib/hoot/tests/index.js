import { start } from "@odoo/hoot";
import { whenReady } from "@odoo/owl";

import "./core/runner.test.js";
import "./core/suite.test.js";
import "./core/test.test.js";
import "./helpers/time.test.js";
import "./hoot-dom/dom.test.js";
import "./hoot-dom/events.test.js";
import "./hoot_utils.test.js";
import "./mock/network.test.js";

whenReady(start);
