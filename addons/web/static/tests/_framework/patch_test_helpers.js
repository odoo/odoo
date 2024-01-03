/** @odoo-module */

import { after } from "@odoo/hoot";
import { patch } from "@web/core/utils/patch";

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/** @type {typeof patch} */
export function patchWithCleanup(obj, patchValue) {
    after(patch(obj, patchValue));
}
