/**@odoo-module */
/*
 *  Convert a timestamp measured in seconds since the Unix epoch. String format returned YYYY-MM-DDThh:mm:ss
 */

export function convertFromEpoch(seconds) {
    return new Date(seconds * 1000).toISOString().substring(0, 19).replace("T", " ");
}
