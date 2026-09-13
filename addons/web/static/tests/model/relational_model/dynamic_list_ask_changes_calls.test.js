// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { Mutex } from "@web/core/utils/concurrency";
import { DynamicList } from "@web/model/relational_model/dynamic_list";

describe.current.tags("headless");

/** @param {{ hasEditedRecord: boolean }} options */
function makeList({ hasEditedRecord }) {
    const list = Object.create(DynamicList.prototype);
    list._config = { resModel: "res.partner" };
    let askChangesCalls = 0;
    const record = {
        isInEdition: true,
        isNew: false,
        dirty: false,
        checkValidityLocked: () => true,
        saveLocked: async () => true,
        discardLocked() {},
        config: {},
        id: "rec_1",
    };
    list._records = hasEditedRecord ? [record] : [];
    Object.defineProperty(list, "records", { get: () => list._records });
    list.removeRecords = () => {};
    list.model = {
        urgentSave: { isActive: false },
        mutex: new Mutex(),
        closeUrgentSaveNotification() {},
        askChanges: async () => {
            askChangesCalls++;
        },
        patchConfig: (/** @type {any} */ config, /** @type {any} */ patch) =>
            Object.assign(config, patch),
    };
    return { list, counts: () => askChangesCalls };
}

describe("leaveEditMode settle barriers", () => {
    test("the save path runs the barrier TWICE for one leave", async () => {
        const { list, counts } = makeList({ hasEditedRecord: true });
        await list.leaveEditMode();
        expect(counts()).toBe(2);
    });

    test("the discard path runs it once", async () => {
        const { list, counts } = makeList({ hasEditedRecord: true });
        await list.leaveEditMode({ discard: true });
        expect(counts()).toBe(1);
    });

    test("with no row in edition it never runs", async () => {
        const { list, counts } = makeList({ hasEditedRecord: false });
        await list.leaveEditMode();
        expect(counts()).toBe(0);
    });
});
