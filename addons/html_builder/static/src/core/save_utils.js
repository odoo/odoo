import { uniqueId } from "@web/core/utils/functions";

/**
 * Build the key under which the elements of a given record's field are grouped
 * to be saved together.
 *
 * @param {string} model
 * @param {string|number} recordId
 * @param {string} field
 * @returns {string}
 */
export function getRecordKey(model, recordId, field) {
    return `${model}::${recordId}::${field}`;
}

/**
 * Group the elements which are from the same field of the same record.
 *
 * @param {Iterable<HTMLElement>} toGroupEls
 * @returns {Object.<string, HTMLElement[]>}
 */
export function groupElements(toGroupEls) {
    return Object.groupBy(toGroupEls, (toGroupEl) => {
        const model = toGroupEl.dataset.oeModel;
        const recordId = toGroupEl.dataset.oeId;
        const field = toGroupEl.dataset.oeField;

        // There are elements which have no linked model as something
        // special is to be done "to save them". In that case, do not group
        // those elements.
        if (!model) {
            return uniqueId("special-element-to-save-");
        }

        return getRecordKey(model, recordId, field);
    });
}
