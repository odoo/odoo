/** @odoo-module */

import { createMock } from "../hoot_utils";

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const { Object, navigator, Reflect } = globalThis;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export class MockClipboard {
    /** @type {any} */
    #value = null;

    async read() {
        return this.readSync();
    }

    async readText() {
        return this.readTextSync();
    }

    async write(value) {
        return this.writeSync(value);
    }

    async writeText(value) {
        return this.writeTextSync(value);
    }

    // Methods below are not part of the Clipboard API but are useful to make
    // test events synchronous.

    /**
     * @returns {any}
     */
    readSync() {
        return this.#value;
    }

    /**
     * @returns {string}
     */
    readTextSync() {
        return String(this.#value ?? "");
    }

    /**
     * @param {any} value
     */
    writeSync(value) {
        this.#value = value;
    }

    /**
     * @param {string} value
     */
    writeTextSync(value) {
        this.#value = String(value ?? "");
    }
}

/** @type {typeof window.Math} */
export const mockNavigator = createMock(navigator, {
    clipboard: { value: new MockClipboard() },
});
