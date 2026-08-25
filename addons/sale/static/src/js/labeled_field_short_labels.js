import { _t } from "@web/core/l10n/translation";

/**
 * Abbreviated labels displayed in front of the fields that are stacked inside a
 * single list view cell, by field name.
 *
 * The mapping can only be built once the translations are loaded, hence the
 * function: at module load time, `_t` returns a lazy string that cannot be
 * evaluated yet.
 *
 * @return {Object} The abbreviated labels, by field name.
 */
function getShortLabels() {
    return {
        margin: _t("M:"),
        margin_percent: _t("M%:"),
        price_total: _t("TI:"),
        price_subtotal: _t("TE:"),
        qty_delivered_percent: _t("D%:"),
    };
}

/**
 * Get the abbreviated label of the provided field.
 *
 * The full label is kept everywhere else (e.g. in the optional columns
 * dropdown), only the stacked field itself is abbreviated.
 *
 * @param {String} name The field name.
 * @return {String|undefined} The abbreviated label, if the field has one.
 */
export function getShortLabel(name) {
    return getShortLabels()[name];
}
