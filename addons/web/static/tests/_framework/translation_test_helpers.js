import { after } from "@odoo/hoot";
import {
    loadLanguages,
    translatedTerms,
    translatedTermsGlobal,
    translationLoaded,
} from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { serverState } from "./mock_server_state.hoot";

/**
 * @param {Record<string, string>} languages
 */
export function installLanguages(languages) {
    serverState.multiLang = true;
    patch(loadLanguages, {
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
            patch(translatedTerms, { [addonName]: {} });
        }
        patch(translatedTerms[addonName], terms[addonName]);
        patch(translatedTermsGlobal, terms[addonName]);
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
