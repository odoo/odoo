/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { toRaw, useState, useEnv, reactive, onMounted, onWillUnmount, markRaw } from "@odoo/owl";
import { Reactive } from "@web_studio/client_action/utils";

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { KeepLast } from "@web/core/utils/concurrency";

/**
 * Provides standard shortcuts for the ActionEditor and  ViewEditor.
 * Used as a communcation interface between the editorMenu
 * and the ActionEditor or the ViewEditor
 *
 * Supports snackBar, breadcrumbs, operation stack
 */
export class EditionFlow extends Reactive {
    constructor(env, services) {
        super();
        this.env = env;
        for (const [servName, serv] of Object.entries(services)) {
            this[servName] = serv;
        }
        this.setup();
    }
    setup() {
        let requestId;
        const updateBreadcrumbs = (studio) => {
            if (studio.requestId !== requestId) {
                this.breadcrumbs = [];
            }
            requestId = studio.requestId;
        };
        const studio = reactive(this.studio, () => updateBreadcrumbs(studio));
        this.studio = studio;
        this.breadcrumbs = [];
        updateBreadcrumbs(studio);
    }

    pushBreadcrumb(crumb) {
        const bcLength = this.breadcrumbs.length;
        const handler = () => {
            this.breadcrumbs.length = bcLength + 1;
            // Reset studio to its own state
            // In case another action has been done
            this.studio.setParams({}, false);
        };
        this.breadcrumbs.push({ data: crumb, handler });
    }

    async loadViews({ forceSearch = false } = {}) {
        const editedAction = this.studio.editedAction;
        const { context, res_model, id } = editedAction;
        const views = [...editedAction.views];
        if (forceSearch && !views.some((tuple) => tuple[1] === "search")) {
            views.push([false, "search"]);
        }
        const newContext = { ...context, lang: false };
        const options = { loadIrFilters: true, loadActionMenus: false, id, studio: true };
        const res = await this.view.loadViews(
            { resModel: res_model, views, context: newContext },
            options
        );
        return JSON.parse(JSON.stringify(res));
    }
    restoreDefaultView(viewId, viewType) {
        return new Promise((resolve) => {
            const confirm = async () => {
                if (!viewId && viewType) {
                    // To restore the default view from an inherited one, we need first to retrieve the default view id
                    const result = await this.loadViews();
                    viewId = result.views[viewType].id;
                }
                const res = await rpc("/web_studio/restore_default_view", {
                    view_id: viewId,
                });
                this.env.bus.trigger("CLEAR-CACHES");
                resolve(res);
            };
            this.dialog.add(ConfirmationDialog, {
                body: _t(
                    "Are you sure you want to restore the default view?\r\nAll customization done with studio on this view will be lost."
                ),
                confirm,
                cancel: () => resolve(false),
            });
        });
    }
}

export function useEditorBreadcrumbs(initialCrumb) {
    const env = useEnv();
    const editionFlow = env.editionFlow;

    if (initialCrumb && !editionFlow.breadcrumbs.length) {
        onMounted(() => editionFlow.pushBreadcrumb(initialCrumb));
    }

    const crumbs = useState(editionFlow.breadcrumbs);
    const push = (crumb) => editionFlow.pushBreadcrumb(crumb);
    return { crumbs, push };
}

export function useEditorMenuItem(MenuItem) {
    const editionFlow = useEnv().editionFlow;
    onMounted(() => {
        editionFlow.MenuItem = MenuItem;
    });
    onWillUnmount(() => {
        if (toRaw(editionFlow).MenuItem === MenuItem) {
            editionFlow.MenuItem = null;
        }
    });
}

/**
 * Indicates whether a the concrete editor has finished its async operation
 * with its state: loaded/loading
 */

// PAss state instead of proms
// PAss count ? => error handling ?
// ecrase prom precedente ?
//
export class SnackbarIndicator extends Reactive {
    constructor() {
        super();
        this.state = "";
        this.keepLast = markRaw(new KeepLast());
    }

    add(prom) {
        this.state = "loading";
        const raw = this.raw();
        this.pending = Promise.all([raw.pending, prom]);

        this.keepLast
            .add(raw.pending)
            .then(() => (this.state = "loaded"))
            .catch(() => {
                this.state = "error";
            })
            .finally(() => {
                this.pending = null;
            });
        return prom;
    }
}

/**
 * A Class that manages undo/redo of some operations
 * in a sort of MutexedKeeLast: doing many calls to "do"
 * will just store the arguments and keep only the last call's results
 */
export class EditorOperations extends Reactive {
    constructor(params) {
        super();
        this.operations = [];
        this.undone = [];
        this._lock = "";
        this._keepLast = markRaw(new KeepLast());

        this._callbacks = {
            do: params.do,
            onError: params.onError,
            onDone: params.onDone,
        };
    }

    get canUndo() {
        return this.operations.length || (this.pending && this.pending.length);
    }

    get canRedo() {
        return this.undone.length || (this.pendingUndone && this.pendingUndone.length);
    }

    _wrapPromise(prom) {
        return this._keepLast.add(prom);
    }

    _prepare(mode) {
        const raw = this.raw();
        const lock = raw._lock;
        if (lock && lock !== mode) {
            this._wrapPromise(Promise.resolve());
            this._close();
            return false;
        }
        this._lock = mode;
        const pending = raw.pending;
        if (!pending) {
            this.pending = [...raw.operations];
            this.pendingUndone = [...raw.undone];
        }
        return true;
    }

    async _do(mode, pending, lastOp) {
        let result;
        let error;
        try {
            result = await this._wrapPromise(
                this._callbacks.do({ mode, operations: pending, lastOp })
            );
        } catch (e) {
            error = e;
        }
        if (error) {
            return { error };
        }
        return { result };
    }

    _close(done = null) {
        const raw = this.raw();
        const mode = raw._lock;
        this._lock = null;
        const pending = raw.pending;
        const pendingUndone = raw.pendingUndone;
        this.pending = null;
        this.pendingUndone = null;

        if (!done) {
            return;
        }

        if ("result" in done) {
            this.operations = pending;
            this.undone = pendingUndone;
            if (typeof done.result !== "boolean") {
                return this._callbacks.onDone({
                    mode,
                    pending,
                    pendingUndone,
                    result: done.result,
                });
            }
        }
        if ("error" in done) {
            return this._callbacks.onError({ mode, pending, error: done.error });
        }
    }

    async undo(canRedo = true) {
        if (!this._prepare("undo")) {
            this._close();
            return;
        }
        const ops = this.raw().pending;
        if (!ops || !ops.length) {
            this._close();
            return;
        }
        const op = ops.pop();
        if (canRedo) {
            this.pendingUndone.push(op);
        }
        const done = await this._do("undo", this.raw().pending, op);
        this._close(done);
    }

    pushOp(op) {
        this.operations.push(op);
    }

    async redo() {
        if (!this._prepare("redo")) {
            this._close();
            return;
        }

        const ops = this.raw().pendingUndone;
        if (!ops || !ops.length) {
            this._close();
            return;
        }
        const op = ops.pop();
        this.pending.push(op);
        const done = await this._do("do", this.raw().pending, op);
        this._close(done);
    }

    async doMulti(ops = []) {
        if (!ops.length) {
            return;
        }
        let prom;
        for (let i = 0; i < ops.length; i++) {
            let silent = true;
            if (i === ops.length - 1) {
                silent = false;
            }
            prom = this.do(ops[i], silent);
        }
        return prom;
    }

    async do(op, silent = false) {
        if (!this._prepare("do") || !op) {
            this._close();
            return;
        }
        this.pending.push(op);
        this.pendingUndone = [];
        let done = {};
        if (!silent) {
            done = await this._do("do", this.raw().pending, op);
        } else {
            done = { result: true };
        }
        this._close(done);
    }

    clear(all = true) {
        this.operations = [];
        if (all) {
            this.undone = [];
        }
    }
}
