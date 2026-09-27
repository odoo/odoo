/** @odoo-module */

import { MockEventTarget } from "../hoot_utils";
import { logger } from "../core/logger";

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    console,
    Object: { keys: $keys },
} = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

const DISPATCHING_METHODS = ["error", "trace", "warn"];

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export class MockConsole extends MockEventTarget {
    static {
        for (const fnName of $keys(console)) {
            if (DISPATCHING_METHODS.includes(fnName)) {
                const fn = logger[fnName];
                this.prototype[fnName] = function (...args) {
                    this.dispatchEvent(new CustomEvent(fnName, { detail: args }));
                    return fn.apply(this, arguments);
                };
            } else {
                this.prototype[fnName] = console[fnName];
            }
        }
    }
}
