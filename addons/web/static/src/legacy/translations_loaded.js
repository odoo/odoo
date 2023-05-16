/** @odoo-module alias=web.legacy_tranlations_loaded */

// this module is imported through its alias to ensure translations are loaded
// before a module definition is executed, this will be insured by the odoo
// module system and is required for defining tours with translated content.

import { is_bound } from "web.session";
export default is_bound;
