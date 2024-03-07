import { after } from "@odoo/hoot";
import { mockDate, mockTimeZone } from "@odoo/hoot-mock";
import { translatedTerms, translationLoaded } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

const { FixedOffsetZone, IANAZone, Settings } = luxon;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/** @type {typeof mockDate} */
export function patchDate(date, tz) {
    mockDate(date);

    if (tz !== undefined && tz !== null) {
        patchTimeZone(tz);
    }
}

/** @type {typeof mockTimeZone} */
export function patchTimeZone(tz) {
    mockTimeZone(tz);

    let defaultZone;
    if (typeof tz === "string") {
        defaultZone = IANAZone.create(tz);
    } else {
        const offset = new Date().getTimezoneOffset();
        defaultZone = FixedOffsetZone.instance(-offset);
    }
    patchWithCleanup(Settings, { defaultZone });
}

/**
 * @param {Record<string, string>} [terms]
 */
export function patchTranslations(terms = {}) {
    translatedTerms[translationLoaded] = true;
    after(() => {
        translatedTerms[translationLoaded] = false;
    });
    patchWithCleanup(translatedTerms, terms);
}

/** @type {typeof patch} */
export function patchWithCleanup(obj, patchValue) {
    after(patch(obj, patchValue));
}
