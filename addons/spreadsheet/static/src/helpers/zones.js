/** @odoo-module */

import { helpers } from "@odoo/o-spreadsheet";
const { overlap, union } = helpers;

/**
 *
 * @typedef Zone
 * @property {number} top
 * @property {number} bottom
 * @property {number} left
 * @property {number} right
 */

/**
 * Check if two zones are contiguous, ie. that they share a border
 *
 * @param {Zone} zone1
 * @param {Zone} zone2
 * @returns {boolean}
 */
export function areZoneContiguous(zone1, zone2) {
    const u = union(zone1, zone2);
    if (zone1.right + 1 === zone2.left || zone1.left === zone2.right + 1) {
        return u.bottom - u.top <= zone1.bottom - zone1.top + (zone2.bottom - zone2.top);
    }
    if (zone1.bottom + 1 === zone2.top || zone1.top === zone2.bottom + 1) {
        return u.right - u.left <= zone1.right - zone1.left + (zone2.right - zone2.left);
    }
    return false;
}

/**
 * Merge contiguous and overlapping zones into bigger zones
 *
 * @param {Array<Zone>} zones
 * @returns {Array<Zone>}
 */
export function mergeContiguousZones(zones) {
    const mergedZones = [...zones];
    let hasMerged = true;
    while (hasMerged) {
        hasMerged = false;
        for (let i = 0; i < mergedZones.length; i++) {
            const zone = mergedZones[i];
            const mergeableZoneIndex = mergedZones.findIndex(
                (z, j) => i !== j && (areZoneContiguous(z, zone) || overlap(z, zone))
            );
            if (mergeableZoneIndex !== -1) {
                mergedZones[i] = union(mergedZones[mergeableZoneIndex], zone);
                mergedZones.splice(mergeableZoneIndex, 1);
                hasMerged = true;
                break;
            }
        }
    }
    return mergedZones;
}
