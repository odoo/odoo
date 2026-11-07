import { after, onTimeZoneChange } from "@odoo/hoot";
import { getRunner } from "@web/../lib/hoot/main_runner";
import { patch } from "@web/core/utils/patch";

const { FixedOffsetZone, IANAZone, Settings } = luxon;

onTimeZoneChange((tz) => {
    let defaultZone;
    if (typeof tz === "string") {
        defaultZone = IANAZone.create(tz);
    } else {
        const offset = new Date().getTimezoneOffset();
        defaultZone = FixedOffsetZone.instance(-offset);
    }
    patchWithCleanup(Settings, { defaultZone });
});

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/** @type {typeof patch} */
export function patchWithCleanup(obj, patchValue) {
    if (getRunner().dry) {
        return () => {};
    }
    const unpatch = patch(obj, patchValue);
    after(unpatch);
    return unpatch;
}
