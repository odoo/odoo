import { Plugin } from "@html_editor/plugin";
import { useComponent } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Operation } from "./operation";

/** @typedef {import("./operation").OperationParams} OperationParams */

/**
 * @typedef { Object } OperationShared
 * @property { OperationPlugin['next'] } next
 */

export class OperationPlugin extends Plugin {
    static id = "operation";
    static dependencies = ["history"];
    static shared = ["next", "hasTimedOut"];

    setup() {
        this._hasTimedOut = false;
        this.operation = new Operation(this.document);

        // Revert any potential preview as soon as the user does anything, to
        // avoid losing what the user will have done when they ends the preview.
        // If there is async action ongoing, like an async apply from a preview,
        // this may lose the user input while the apply was running
        this.addDomListener(this.editable, "keydown", () => this.next());
        this.addDomListener(this.editable, "beforeinput", () => this.next());
    }

    /**
     * Executes a function (async or not) in the mutex.
     *
     * @param {Function} fn the function
     * @param {OperationParams} params
     * @returns {Promise<void>}
     */
    async next(fn, params = { canTimeout: false }) {
        let rollback;
        const result = await this.operation.next(() => {
            if (params.canTimeout) {
                rollback = this.dependencies.history.makeSavePoint();
            }
            if (fn) {
                return fn();
            }
        }, params);
        if (result && result.hasFailed && rollback) {
            this._hasTimedOut = true;
            this.onTimeout(rollback);
        }
        return result;
    }

    onTimeout(rollback) {
        rollback();

        this.services.notification.add(
            _t(
                "A technical issue occurred in the builder, you should save or discard your changes."
            ),
            {
                type: "danger",
                sticky: true,
            }
        );
    }

    hasTimedOut() {
        return this._hasTimedOut;
    }
}

export function useOperation() {
    const comp = useComponent();
    return (apply, ...args) => {
        comp.env.editor.shared.operation.next(async (...args) => {
            await apply(...args);
            comp.env.editor.shared.history.addStep();
        }, ...args);
    };
}
