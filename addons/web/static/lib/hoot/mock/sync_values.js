/** @odoo-module */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const { Blob, TextEncoder } = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

const syncValues = new WeakMap();

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @param {any} object
 */
export function getSyncValue(object) {
    return syncValues.get(object);
}

/**
 * @param {any} object
 * @param {any} value
 */
export function setSyncValue(object, value) {
    syncValues.set(object, value);
}

export class MockBlob extends Blob {
    constructor(blobParts, options) {
        super(blobParts, options);

        setSyncValue(this, blobParts);
    }

    async arrayBuffer() {
        return new TextEncoder().encode(getSyncValue(this));
    }

    async text() {
        return getSyncValue(this).join("");
    }
}
