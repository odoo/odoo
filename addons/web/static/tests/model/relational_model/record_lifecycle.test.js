// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { markRaw } from "@odoo/owl";
import { MODEL_LIFECYCLE_PROTO } from "@web/../tests/model/relational_model/model_doubles";
import { makeTestRelationalModel } from "@web/../tests/model/relational_model/model_test_helpers";
import {
    installEditState,
    RECORD_STATE_TRANSITIONS,
} from "@web/../tests/model/relational_model/record_doubles";
import { makeLogger } from "@web/core/debug/debug_logger";
import { makeActiveField } from "@web/model/relational_model/field_metadata";
import {
    archive,
    deleteRecord,
    duplicateRecord,
    unarchive,
} from "@web/model/relational_model/record_lifecycle";

/**
 * @param {Object} [opts]
 * @param {number|false} [opts.resId=1]
 * @param {number[]} [opts.resIds=[1]]
 * @param {Function|null} [opts.unlink]
 * @param {Function|null} [opts.call]
 * @param {Function|null} [opts.load]
 * @param {Function|null} [opts.onDisplayArchiveAction]
 * @returns {Object}
 */
function makeRecord({
    resId = 1,
    resIds = [1],
    unlink = null,
    call = null,
    load = null,
    onDisplayArchiveAction = null,
} = {}) {
    /** @type {any} */
    const record = {
        resId,
        resIds,
        resModel: "res.partner",
        context: { uid: 1 },
        config: { resId, resIds, context: { uid: 1 } },
        _values: markRaw({ id: resId, name: "Test" }),
        get savedData() {
            return this._values;
        },
        _textValues: markRaw({ name: "Test" }),
        changes: markRaw({}),
        data: { id: resId, name: "Test" },
        parseServerValues(defaults) {
            return { ...defaults };
        },
        getDefaultValues() {
            return { id: false, name: false };
        },
        ...RECORD_STATE_TRANSITIONS,
        _clearChanges() {
            this.changes = markRaw({});
            this.dirty = false;
        },
        setEvalContext() {},
        loadLocked: async () => {},
        model: {
            orm: {
                unlink: unlink ?? (async () => true),
                call:
                    call ??
                    (async (model, method) => {
                        if (method === "copy") {
                            return [Number(resId) * 10];
                        }
                        return false;
                    }),
            },
            load: load ?? (async () => {}),
            patchConfig: () => {},
            __proto__: MODEL_LIFECYCLE_PROTO,
            hooks: {
                ui: {
                    onDisplayArchiveAction:
                        onDisplayArchiveAction ?? ((_action, reload) => reload()),
                },
                lifecycle: {},
            },
        },
    };
    installEditState(record);
    return record;
}

describe("archive / unarchive ORM method routing", () => {
    test("archive() calls orm.call with 'action_archive'", async () => {
        let calledMethod = null;
        const rec = makeRecord({
            call: async (_model, method) => {
                calledMethod = method;
                return false;
            },
        });
        await archive(rec);
        expect(calledMethod).toBe("action_archive");
    });

    test("unarchive() calls orm.call with 'action_unarchive'", async () => {
        let calledMethod = null;
        const rec = makeRecord({
            call: async (_model, method) => {
                calledMethod = method;
                return false;
            },
        });
        await unarchive(rec);
        expect(calledMethod).toBe("action_unarchive");
    });

    test("archive() passes [[resId]] as args and {context} as kwargs", async () => {
        let capturedArgs = null;
        let capturedKwargs = null;
        const rec = makeRecord({
            resId: 42,
            call: async (_model, _method, args, kwargs) => {
                capturedArgs = args;
                capturedKwargs = kwargs;
                return false;
            },
        });
        rec.context = { lang: "en_US", uid: 7 };
        await archive(rec);
        expect(capturedArgs).toEqual([[42]]);
        expect(capturedKwargs).toEqual({ context: { lang: "en_US", uid: 7 } });
    });
});

describe("archive hook routing", () => {
    test("server action result is forwarded to hooks.ui.onDisplayArchiveAction", async () => {
        const serverAction = { type: "ir.actions.act_window", res_id: 99 };
        let receivedAction = null;
        const rec = makeRecord({
            call: async () => serverAction,
            onDisplayArchiveAction: (action) => {
                receivedAction = action;
                return "hook-return-value";
            },
        });
        const result = await archive(rec);
        expect(receivedAction).toBe(serverAction);
        expect(result).toBe("hook-return-value");
    });

    test("the reload callback passed to the hook invokes record.loadLocked", async () => {
        let loadCalled = false;
        const rec = makeRecord({
            onDisplayArchiveAction: (_action, reload) => reload(),
        });
        rec.loadLocked = async () => {
            loadCalled = true;
        };
        await archive(rec);
        expect(loadCalled).toBe(true);
    });
});

describe("deleteRecord veto", () => {
    test("returns false when orm.unlink returns falsy and does not mutate state", async () => {
        let loadCalled = false;
        let clearChangesCalled = false;
        const rec = makeRecord({
            unlink: async () => false,
            load: async () => {
                loadCalled = true;
            },
        });
        rec._clearChanges = () => {
            clearChangesCalled = true;
        };
        const result = await deleteRecord(rec);
        expect(result).toBe(false);
        expect(loadCalled).toBe(false);
        expect(clearChangesCalled).toBe(false);
    });
});

describe("deleteRecord navigation", () => {
    test("with non-last position, navigates to the next record in resIds", async () => {
        let loadArgs = null;
        const rec = makeRecord({
            resId: 5,
            resIds: [3, 5, 7, 9],
            load: async (args) => {
                loadArgs = args;
            },
        });
        await deleteRecord(rec);
        expect(loadArgs).toEqual({ resId: 7, resIds: [3, 7, 9] });
    });

    test("with last position, navigates to the previous record in resIds", async () => {
        let loadArgs = null;
        const rec = makeRecord({
            resId: 9,
            resIds: [3, 5, 7, 9],
            load: async (args) => {
                loadArgs = args;
            },
        });
        await deleteRecord(rec);
        expect(loadArgs).toEqual({ resId: 7, resIds: [3, 5, 7] });
    });

    test("resId absent from resIds: navigates to the first remaining record, no data loss", async () => {
        let loadArgs = null;
        const rec = makeRecord({
            resId: 999,
            resIds: [3, 5, 7],
            load: async (args) => {
                loadArgs = args;
            },
        });
        await deleteRecord(rec);
        expect(loadArgs).toEqual({ resId: 3, resIds: [3, 5, 7] });
    });
});

describe("deleteRecord state reset (last record)", () => {
    test("when resIds becomes empty, resets _values / _textValues / changes / data", async () => {
        let loadCalled = false;
        let patchConfigArgs = null;
        let setEvalContextCalled = false;
        const rec = makeRecord({
            resId: 1,
            resIds: [1],
            load: async () => {
                loadCalled = true;
            },
        });
        rec.model.patchConfig = (_config, patch) => {
            patchConfigArgs = { patch };
        };
        rec.setEvalContext = () => {
            setEvalContextCalled = true;
        };
        await deleteRecord(rec);
        expect(loadCalled).toBe(false);
        expect(patchConfigArgs).toEqual({
            patch: { resId: false, resIds: [] },
        });
        expect(rec._textValues).toEqual({});
        expect(rec._values).toEqual({ id: false, name: false });
        expect(rec.data).toEqual({ id: false, name: false });
        expect(rec.dirty).toBe(false);
        expect(setEvalContextCalled).toBe(true);
    });
});

describe("duplicateRecord", () => {
    test("calls orm.call with 'copy' passing [[resId]]", async () => {
        let copyArgs = null;
        const rec = makeRecord({
            resId: 7,
            call: async (_model, method, args) => {
                if (method === "copy") {
                    copyArgs = args;
                    return [42];
                }
                return false;
            },
        });
        await duplicateRecord(rec);
        expect(copyArgs).toEqual([[7]]);
    });

    test("inserts the new resId immediately AFTER the source in resIds", async () => {
        let loadArgs = null;
        const rec = makeRecord({
            resId: 5,
            resIds: [3, 5, 7, 9],
            call: async (_model, method) => {
                if (method === "copy") {
                    return [42];
                }
                return false;
            },
            load: async (args) => {
                loadArgs = args;
            },
        });
        await duplicateRecord(rec);
        expect(loadArgs).toEqual({
            resId: 42,
            resIds: [3, 5, 42, 7, 9],
            mode: "edit",
        });
    });

    test("navigation uses mode 'edit' so the duplicate is immediately editable", async () => {
        let loadMode = null;
        const rec = makeRecord({
            call: async (_model, method) => {
                if (method === "copy") {
                    return [99];
                }
                return false;
            },
            load: async (args) => {
                loadMode = args.mode;
            },
        });
        await duplicateRecord(rec);
        expect(loadMode).toBe("edit");
    });

    test("copy passes {context} as kwargs", async () => {
        let copyKwargs = null;
        const rec = makeRecord({
            call: async (_model, method, _args, kwargs) => {
                if (method === "copy") {
                    copyKwargs = kwargs;
                    return [99];
                }
                return false;
            },
        });
        rec.context = { default_user_id: 3, lang: "fr_FR" };
        await duplicateRecord(rec);
        expect(copyKwargs).toEqual({
            context: { default_user_id: 3, lang: "fr_FR" },
        });
    });
});

async function makeLifecycleModel() {
    const model = await makeTestRelationalModel({
        loadRecords: async (config) => [{ id: config.resId, name: "Test" }],
    });
    model.patchConfig(model.config, {
        isMonoRecord: true,
        mode: "readonly",
        resId: 1,
        resIds: [1],
        fields: { name: { name: "name", type: "char" } },
        activeFields: { name: makeActiveField() },
    });
    await model.load();
    return model;
}

test("deleting the last record removes its id from the live navigation state", async () => {
    const model = await makeLifecycleModel();
    model.orm = { ...model.orm, unlink: async () => true };
    await model.root.delete();
    expect(model.root.resId).toBe(false);
    expect(model.root.resIds).toEqual([]);
    expect(model.config.resIds).toEqual([]);
    model.loadNewRecord = async () => ({ name: "" });
    await model.load();
    expect(model.root.isInEdition).toBe(true);
    await model.root.update({ name: "Replacement" }, { withoutOnchange: true });
    model.orm = {
        ...model.orm,
        webSave: async (_model, ids, values) => {
            expect(ids).toEqual([]);
            expect(values).toEqual({ name: "Replacement" });
            return [{ id: 42, name: "Replacement" }];
        },
    };
    await model.root.save();
    makeLogger("web.model.audit").logic("delete then create navigation", {
        resId: model.root.resId,
        resIds: model.root.resIds,
    });
    expect(model.root.resIds).toEqual([42]);
    expect(model.root.resId).toBe(42);
});

test("duplicating a readonly record loads the actual new root in edit mode", async () => {
    const model = await makeLifecycleModel();
    model.orm = { ...model.orm, call: async () => [42] };
    await model.root.duplicate();
    expect(model.root.resId).toBe(42);
    expect(model.root.resIds).toEqual([1, 42]);
    expect(model.root.isInEdition).toBe(true);
    expect(model.config.mode).toBe("edit");
});

test("failed duplicate loading preserves the original root and readonly mode", async () => {
    const model = await makeLifecycleModel();
    const original = model.root;
    model.orm = { ...model.orm, call: async () => [42] };
    model.loadRecords = async () => {
        throw new Error("read failed");
    };
    let failure;
    try {
        await model.root.duplicate();
    } catch (error) {
        failure = error;
    }
    makeLogger("web.model.audit").logic("duplicate read failure", {
        failure: failure?.message,
        mode: model.config.mode,
        resIds: model.config.resIds,
    });
    expect(failure?.message).toBe("read failed");
    expect(model.root).toBe(original);
    expect(model.root.resIds).toEqual([1]);
    expect(model.config.mode).toBe("readonly");
    model.loadRecords = async () => [{ id: 1, name: "Test" }];
    await model.load({ mode: "edit" });
    expect(model.root.isInEdition).toBe(true);
    await model.load({ mode: "readonly" });
    expect(model.root.isInEdition).toBe(false);
});
