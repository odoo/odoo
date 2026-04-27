/** @odoo-module */
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

import { reactive, useComponent, useEnv, toRaw, onMounted, onWillDestroy } from "@odoo/owl";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { Deferred } from "@web/core/utils/concurrency";
import { registry } from "@web/core/registry";

/**
 * An customization of @web/core/timing/batched that allows two things:
 * - store call arguments as long as we have not passed the synchronize timing
 * - returns the same promise to each caller that will be resolved when callback has finished
 * @param {Function} callback
 * @param {Function} synchronize
 * @returns Function
 */
function batched(callback, synchronize = () => Promise.resolve()) {
    const map = new Map();
    let callId = 0;
    return (...args) => {
        if (!map.has(callId)) {
            const argsList = [args];
            const prom = new Deferred();
            map.set(callId, { argsList, prom });
            synchronize().then(() => {
                const currentCallId = callId++;
                Promise.resolve(callback(...argsList))
                    .then(prom.resolve)
                    .catch(prom.reject)
                    .finally(() => map.delete(currentCallId));
            });
            return prom;
        } else {
            const { prom, argsList } = map.get(callId);
            argsList.push(args);
            return prom;
        }
    };
}

export function buildApprovalKey(...args) {
    return args.join("-");
}

export const getApprovalSpecBatchedService = {
    name: "web_studio.get_approval_spec_batched",
    dependencies: ["orm"],
    start(env, { orm }) {
        return batched(async (...argsLists) => {
            const approvals = await orm.silent.call("studio.approval.rule", "get_approval_spec", [
                argsLists.flat(),
            ]);

            for (const [key, tupleList] of Object.entries(approvals)) {
                if (key === "all_rules") {
                    continue;
                }
                approvals[key] = Object.fromEntries(
                    tupleList.map(([tuple, value]) => {
                        return [buildApprovalKey(...tuple), value];
                    })
                );
            }

            return approvals;
        });
    },
};

registry
    .category("services")
    .add(getApprovalSpecBatchedService.name, getApprovalSpecBatchedService);

function getMissingApprovals(entries, rules) {
    const missingApprovals = [];
    const doneApprovals = entries.filter((e) => e.approved).map((e) => e.rule_id[0]);
    rules.forEach((r) => {
        if (!doneApprovals.includes(r.id)) {
            missingApprovals.push(r);
        }
    });
    return missingApprovals;
}

class StudioApproval {
    constructor({ getApprovalSpecBatched, model }) {
        this._data = reactive({});
        this.model = model;
        this.rules = {};

        const promSet = new WeakSet();
        this.getApprovalSpecBatched = (...args) => {
            const prom = getApprovalSpecBatched(...args);
            if (!promSet.has(prom)) {
                promSet.add(prom);
                prom.then((approvals) => {
                    Object.assign(this.rules, approvals.all_rules);
                });
            }
            return prom;
        };

        // Lazy properties to be set by specialization.
        this.orm = null;
        this.studio = null;
        this.notification = null;
        this.resModel = null;
        this.resId = null;
        this.method = null;
        this.action = null;
    }

    get dataKey() {
        return buildApprovalKey(this.resModel, this.resId || false, this.method, this.action);
    }

    /**
     * The approval's values for a given resModel, resId, method and action.
     * If current values don't exist, we fetch them from the server. Owl's fine reactivity
     * does the update of every component using that state.
     */
    get state() {
        const state = this._getState();
        if (state.rules === null && !state.syncing && !this.willCheck) {
            this.fetchApprovals();
        }
        return state;
    }

    get inStudio() {
        return this.studio;
    }

    displayNotification(data) {
        const missingApprovals = getMissingApprovals(data.entries, data.rules);
        this.notification.add(
            missingApprovals.length > 1
                ? _t("Some approvals are missing")
                : _t("An approval is missing"),
            {
                type: "warning",
            }
        );
    }

    async checkApproval() {
        const args = [this.resModel, this.resId, this.method, this.action];
        const state = this._getState();
        state.syncing = true;
        const result = await this.orm.call("studio.approval.rule", "check_approval", args);
        const approved = result.approved;
        if (!approved) {
            this.displayNotification(result);
        }
        this.willCheck = false;
        this.fetchApprovals(); // don't wait
        return approved;
    }

    async fetchApprovals() {
        const state = this._getState();
        state.syncing = true;
        // In studio we fetch every rule, even if they do not apply
        // to the current record if present
        const resId = !this.inStudio && this.resId;
        try {
            const allApprovals = await this.getApprovalSpecBatched({
                model: this.resModel,
                method: this.method,
                action_id: this.action,
                res_id: resId,
            });
            const myApproval = allApprovals[this.resModel][
                buildApprovalKey(resId, this.method || false, this.action || false)
            ] || { rules: [], entries: [] };
            Object.assign(state, myApproval);
        } catch {
            Object.assign(state, { rules: [], entries: [] });
        } finally {
            state.syncing = false;
        }
    }

    /**
     * Create or update an approval entry for a specified rule server-side.
     * @param {Number} ruleId
     * @param {Boolean} approved
     */
    async setApproval(ruleId, approved) {
        try {
            await this.orm.call("studio.approval.rule", "set_approval", [[ruleId]], {
                res_id: this.resId,
                approved,
            });
        } catch (e) {
            this.fetchApprovals();
            throw e;
        }
        return await this.model.root.load();
    }

    /**
     * Delete an approval entry for a given rule server-side.
     * @param {Number} ruleId
     */
    async cancelApproval(ruleId) {
        try {
            await this.orm.call("studio.approval.rule", "delete_approval", [[ruleId]], {
                res_id: this.resId,
            });
        } catch (e) {
            this.fetchApprovals();
            throw e;
        }
        return this.model.root.load();
    }

    _getState() {
        if (!(this.dataKey in this._data)) {
            this._data[this.dataKey] = { rules: null };
        }
        return this._data[this.dataKey];
    }
}

const approvalMap = new WeakMap();

export function useApproval({ getRecord, method, action }) {
    /* The component using this hook can be destroyed before ever being mounted.
    In practice, we do an rpc call in the component setup without knowing if it will be mounted.
    When a new instance of the component is created, it will share the same data, and the
    promise from `useService("orm")` will never resolve due to the old instance being destroyed.
    What we can do to prevent that, is initially use an unprotected orm and once
    the component has been mounted, we can switch the orm to the one from useService. */
    const protectedOrm = useService("orm");
    const unprotectedOrm = useEnv().services.orm;
    const notification = useService("notification");
    const record = getRecord(useComponent().props);
    const model = toRaw(record.model);
    const getApprovalSpecBatched = useEnv().services["web_studio.get_approval_spec_batched"];
    let approvalModelCache = approvalMap.get(model);
    if (!approvalModelCache) {
        approvalModelCache = {
            approval: new StudioApproval({ getApprovalSpecBatched, model }),
            onRecordSaved: new Map(),
        };
        approvalMap.set(model, approvalModelCache);
        const onRecordSaved = model.hooks.onRecordSaved;
        model.hooks.onRecordSaved = (...args) => {
            approvalModelCache.onRecordSaved.forEach((fn) => fn(args[0]));
            return onRecordSaved(...args);
        };
        const onRootLoaded = model.hooks.onRootLoaded;
        model.hooks.onRootLoaded = (...args) => {
            // nullify every state. This will trigger a re-render and thus
            // a fetch of all approval for buttons that ask for it.
            for (const data of Object.values(approvalModelCache.approval._data)) {
                data.rules = null;
            }
            if (onRootLoaded) {
                return onRootLoaded(...args);
            }
        };
    }

    const specialize = {
        resModel: record.resModel,
        resId: record.resId,
        method,
        action,
        orm: unprotectedOrm,
        studio: !!record.context.studio,
        notification,
    };

    const approval = reactive(
        Object.assign(Object.create(approvalModelCache.approval), specialize)
    );

    approvalModelCache.onRecordSaved.set(toRaw(approval), () => {
        if (!approval.resId && record.resId) {
            approval.resId = record.resId;
        } else {
            delete approval._data[approval.dataKey];
        }
    });
    onWillDestroy(() => approvalModelCache.onRecordSaved.delete(toRaw(approval)));

    useRecordObserver((record) => {
        approval.resId = record.resId;
        approval.resModel = record.resModel;
    });

    onMounted(() => {
        approval.orm = protectedOrm;
    });

    return approval;
}
