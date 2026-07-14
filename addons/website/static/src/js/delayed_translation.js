import { rpc } from "@web/core/network/rpc";
import { groupElements } from "@html_builder/core/save_utils";

/**
 * Save the delayed translations of the records found under `rootEl`, except the
 * ones saved with a new value, which flushes their delayed terms anyway.
 *
 * @param {ParentNode} rootEl - element to search.
 * @param {string} lang - current website language code.
 * @param {Object<string, unknown>} [groupedDirtyElements] - the records saved
 *        with a new value, keyed as in `groupElements`.
 * @returns {Promise}
 */
export function saveDelayTranslations(rootEl, lang, groupedDirtyElements = {}) {
    // Don't take dirty elements as they will be saved
    const cleanDelayTranslationEls = [
        ...rootEl.querySelectorAll(".o_delay_translation:not(.o_dirty)"),
    ];
    const groupedDelayTranslationElements = groupElements(cleanDelayTranslationEls);
    const updateTranslationProms = [];
    const translations = { [lang]: {} };
    for (const [key, els] of Object.entries(groupedDelayTranslationElements)) {
        // Keep only delay translation related to particular field that will
        // not be updated by a modified (dirty) element
        if (groupedDirtyElements[key]) {
            continue;
        }
        updateTranslationProms.push(
            rpc("/website/field/translation/update", {
                model: els[0].dataset["oeModel"],
                record_id: [Number(els[0].dataset["oeId"])],
                field_name: els[0].dataset["oeField"],
                translations,
            })
        );
    }
    return Promise.all(updateTranslationProms);
}
