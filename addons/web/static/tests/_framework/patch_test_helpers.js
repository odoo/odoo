import { after } from "@odoo/hoot";
import { mockTimeZone } from "@odoo/hoot-mock";
import { patch } from "@web/core/utils/patch";

const { FixedOffsetZone, IANAZone, Settings } = luxon;

mockTimeZone.onCall = (tz) => {
    let defaultZone;
    if (typeof tz === "string") {
        defaultZone = IANAZone.create(tz);
    } else {
        const offset = new Date().getTimezoneOffset();
        defaultZone = FixedOffsetZone.instance(-offset);
    }
    patchWithCleanup(Settings, { defaultZone });
};

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/** @type {typeof patch} */
export function patchWithCleanup(obj, patchValue) {
    after(patch(obj, patchValue));
}
