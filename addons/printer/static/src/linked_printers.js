/**
 * The printers a user chose for a report, remembered in their browser.
 *
 * @typedef {Object} LinkedPrinters
 * @property {string} reportName technical name of the report
 * @property {string} displayName name of the report, as it was printed
 * @property {number[]} printerIds ids of the chosen printers
 * @property {boolean} skipDialog print without asking the next times
 */

const STORAGE_PREFIX = "printer.linked_printers.";

/**
 * @param {string} reportName
 * @returns {LinkedPrinters | null}
 */
export function getLinkedPrinters(reportName) {
    try {
        return JSON.parse(localStorage.getItem(STORAGE_PREFIX + reportName));
    } catch {
        return null;
    }
}

/**
 * @param {LinkedPrinters} linkedPrinters
 */
export function setLinkedPrinters({ reportName, displayName, printerIds, skipDialog }) {
    localStorage.setItem(
        STORAGE_PREFIX + reportName,
        JSON.stringify({ reportName, displayName, printerIds, skipDialog })
    );
}

/**
 * @param {string} reportName
 */
export function forgetLinkedPrinters(reportName) {
    localStorage.removeItem(STORAGE_PREFIX + reportName);
}

/**
 * @returns {LinkedPrinters[]}
 */
export function getAllLinkedPrinters() {
    const reportNames = [];
    for (let index = 0; index < localStorage.length; index++) {
        const key = localStorage.key(index);
        if (key.startsWith(STORAGE_PREFIX)) {
            reportNames.push(key.slice(STORAGE_PREFIX.length));
        }
    }
    return reportNames
        .map(getLinkedPrinters)
        .filter(Boolean)
        .sort((a, b) => a.displayName.localeCompare(b.displayName));
}
