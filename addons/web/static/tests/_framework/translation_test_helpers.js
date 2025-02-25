import { after } from "@odoo/hoot";
import { serverState } from "./mock_server_state.hoot";
import { patchWithCleanup } from "./patch_test_helpers";

import { loadLanguages, translatedTerms, translationLoaded } from "@web/core/l10n/translation";

/**
 * @param {Record<string, string>} languages
 */
export function installLanguages(languages) {
    serverState.multiLang = true;
    patchWithCleanup(loadLanguages, {
        installedLanguages: Object.entries(languages),
    });
}

export function allowTranslations() {
    translatedTerms[translationLoaded] = true;
    after(() => {
        translatedTerms[translationLoaded] = false;
    });
}

/**
 * @param {Record<string, Record<string, string>>} [terms]
 */
export function patchTranslations(terms = {}) {
    allowTranslations();
    for (const addonName in terms) {
        if (!(addonName in translatedTerms)) {
            patchWithCleanup(translatedTerms, { [addonName]: {} });
        }
        patchWithCleanup(translatedTerms[addonName], terms[addonName]);
    }
}
