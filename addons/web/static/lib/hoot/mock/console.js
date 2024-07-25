/** @odoo-module */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const { console } = globalThis;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export class MockConsole extends EventTarget {
    static {
        for (const [name, method] of Object.entries(console)) {
            this.prototype[name] = function (...args) {
                this.dispatchEvent(new CustomEvent(name, { detail: args }));
                return method.call(this, ...args);
            };
        }
    }
}
