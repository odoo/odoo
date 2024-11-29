/** @odoo-module */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const { console } = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

const DISPATCHING_METHODS = ["error", "trace", "warn"];

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export class MockConsole extends EventTarget {
    static {
        for (const [name, value] of Object.entries(console)) {
            if (DISPATCHING_METHODS.includes(name)) {
                this.prototype[name] = function (...args) {
                    this.dispatchEvent(new CustomEvent(name, { detail: args }));
                    return value.apply(this, arguments);
                };
            } else {
                this.prototype[name] = value;
            }
        }
    }
}
