/** @odoo-module **/

export const _store = {
    /**
     * All identifiers.
     *
     * - Key: <model.Id>
     * - Value: <structure.Id>
     *
     * @see _id to get a model.Id from data.
     */
    ids: {},
    /**
     * All records.
     *
     * Key: <structure.Id>
     * Value: <structure.Id>
     */
    records: {},
    /*================*
     ||              ||
     ||   Internal   ||
     ||              ||
     *================*/
    /**
     * All primitives (records).
     * Map to corresponding structure.Id of the primitive record from primitive value.
     *
     * Key: <any>
     * Value: <structure.Id>
     */
    primitives: new Map(),
    id_in: '{model.id.in}',
    id_out: '{model.id.out}',
    id_sub_in: '{model.sub.in}',
    id_sub_out: '{model.sub.out}',
    id_sep1: '{model.id.sep1}',
    id_sep2: '{model.id.sep2}',
};
window['model/store'] = _store;
