import { after } from "@odoo/hoot";
import { serverState } from "./mock_server_state.hoot";
import { patchWithCleanup } from "./patch_test_helpers";

import {
    loadLanguages,
    translatedTerms,
    translatedTermsGlobal,
    translationLoaded,
} from "@web/core/l10n/translation";

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
        patchWithCleanup(translatedTermsGlobal, terms[addonName]);
    }
}

function _translate_tree(tree, callback) {
    function translateNode(node) {
        if (node.nodeName.toUpperCase() === "P") {
            const translated = callback(node.innerHTML);
            if (translated) {
                node.innerHTML = translated;
            }
            return;
        } else if (node.nodeName.toUpperCase() === "DIV" && node.hasAttribute("title")) {
            const titleTranslated = callback(node.getAttribute("title"));
            if (titleTranslated) {
                node.setAttribute("title", titleTranslated);
            }
        }
        for (const child of node.children) {
            translateNode(child);
        }
    }
    translateNode(tree);
    return tree;
}

export function xml_translate(callback, value) {
    const tree = new DOMParser().parseFromString(`<div>${value}</div>`, "application/xhtml+xml");
    return _translate_tree(tree.firstElementChild, callback).innerHTML;
}
xml_translate.toJSON = () => true;
