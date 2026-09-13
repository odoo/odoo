// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { RelationalRecord } from "@web/model/relational_model/record";

describe.current.tags("headless");

/**
 * @param {{ urgent?: boolean }} [options]
 * @returns {{ record: any, seen: Record<string, any>[] }}
 */
function makeRecord({ urgent = false } = {}) {
    /** @type {Record<string, any>[]} */
    const seen = [];
    const record = Object.create(RelationalRecord.prototype);
    Object.assign(record, {
        _config: { resModel: "res.partner", resId: 1 },
        model: {
            urgentSave: { isActive: urgent },
            mutex: { exec: (/** @type {() => any} */ fn) => fn() },
        },
        canSaveOnUpdate: false,
        /**
         * @param {Record<string, any>} changes
         * @param {Record<string, any>} options
         * @returns {Promise<undefined>}
         */
        updateLocked: async (changes, options) => {
            seen.push(options);
            return undefined;
        },
    });
    return { record, seen };
}

test("update forwards withoutParentUpdate to updateLocked", async () => {
    const { record, seen } = makeRecord();
    await record.update({ a: 1 }, { withoutParentUpdate: true });
    expect(seen.length).toBe(1);
    expect(seen[0].withoutParentUpdate).toBe(true);
});

test("update forwards it on the urgent-save path too", async () => {
    const { record, seen } = makeRecord({ urgent: true });
    await record.update({ a: 1 }, { withoutParentUpdate: true });
    expect(seen.length).toBe(1);
    expect(seen[0].withoutParentUpdate).toBe(true);
});

test("the option is off unless asked for, and save still drives withoutOnchange", async () => {
    const { record, seen } = makeRecord();
    await record.update({ a: 1 });
    expect(seen[0].withoutParentUpdate).toBe(undefined);
    expect(seen[0].withoutOnchange).toBe(undefined);

    await record.update({ a: 1 }, { save: true });
    expect(seen[1].withoutOnchange).toBe(true);
    expect(seen[1].withoutParentUpdate).toBe(undefined);
});

test("suppressing the parent update does not suppress the save", async () => {
    const { record, seen } = makeRecord();
    let saved = 0;
    record.canSaveOnUpdate = true;
    record.saveLocked = async () => {
        saved++;
    };
    await record.update({ a: 1 }, { save: true, withoutParentUpdate: true });
    expect(seen[0].withoutParentUpdate).toBe(true);
    expect(saved).toBe(1);
});
