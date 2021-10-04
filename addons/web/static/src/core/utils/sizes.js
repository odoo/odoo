/** @odoo-module */

/**
 * Returns a human readable size
 * e.g. 167 => 167 Bytes and 1311 => 1.28 Kb
 *
 * @param {Number} size value in Bytes
 */
export function human_size(size) {
    const units = [ '%s Bytes', '%s Kb', '%s Mb', '%s Gb', '%s Tb' ];
    let i = 0;
    while (size >= 1024 && i < units.length - 1) {
        size /= 1024;
        ++i;
    }
    return _.str.sprintf(
        units[i],
        Number.isInteger(size) ? size : size.toFixed(2)
    );
}
    