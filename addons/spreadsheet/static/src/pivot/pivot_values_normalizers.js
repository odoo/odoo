import { registries, helpers, constants } from "@odoo/o-spreadsheet";

const { DEFAULT_LOCALE } = constants;
const { pivotNormalizationValueRegistry } = registries;
const { toString, toNumber } = helpers;

const STRING_IDS = ["account.root"];

/**
 * Add pivot normalizaton functions to support odoo specific fields
 * in spreadsheet
 */

pivotNormalizationValueRegistry
    .add("text", (value) => toString(value))
    .add("reference", (value) => toString(value))
    .add("selection", (value) => toString(value))
    .add("many2one_reference", (value) => toNumber(value, DEFAULT_LOCALE))
    .add("monetary", (value) => toNumber(value, DEFAULT_LOCALE))
    .add("many2one", (value, dimension) => {
        if (STRING_IDS.includes(dimension.relation)) {
            return toString(value);
        }
        return toNumber(value, DEFAULT_LOCALE);
    })
    .add("many2many", (value) => toNumber(value, DEFAULT_LOCALE))
    .add("float", (value) => toNumber(value, DEFAULT_LOCALE));
