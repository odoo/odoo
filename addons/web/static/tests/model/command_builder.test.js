// @ts-check

/**
 * Pure unit tests for command_builder.js.
 *
 * Tests the x2many command serialization and deduplication logic
 * without OWL, without a browser DOM, and without any mock server.
 */

import { describe, expect, test } from "@odoo/hoot";
import {
    absorbUnlinkIntoSet,
    isUpdateRedundant,
    serializeCommands,
    shouldEmitDelete,
    shouldEmitUnlink,
} from "@web/model/relational_model/command_builder";

// Command constants (mirroring x2ManyCommands)
const CREATE = 0;
const UPDATE = 1;
const DELETE = 2;
const UNLINK = 3;
const LINK = 4;
const SET = 6;

// ---------------------------------------------------------------------------
// serializeCommands
// ---------------------------------------------------------------------------

describe("serializeCommands", () => {
    const fields = { name: { type: "char" } };
    const activeFields = { name: { readonly: false } };

    function makeParams(overrides = {}) {
        return {
            unknownRecordCommands: {},
            fields,
            activeFields,
            context: {},
            withReadonly: false,
            getRecord: () => undefined,
            getRecordChanges: () => ({}),
            convertUnityValues: (v) => v,
            ...overrides,
        };
    }

    test("passes through DELETE commands unchanged", () => {
        const commands = [[DELETE, 1]];
        const result = serializeCommands(commands, makeParams());
        expect(result).toEqual([[DELETE, 1]]);
    });

    test("passes through UNLINK commands unchanged", () => {
        const commands = [[UNLINK, 5]];
        const result = serializeCommands(commands, makeParams());
        expect(result).toEqual([[UNLINK, 5]]);
    });

    test("passes through LINK commands unchanged", () => {
        const commands = [[LINK, 3]];
        const result = serializeCommands(commands, makeParams());
        expect(result).toEqual([[LINK, 3]]);
    });

    test("passes through SET commands unchanged", () => {
        const commands = [[SET, false, [1, 2, 3]]];
        const result = serializeCommands(commands, makeParams());
        expect(result).toEqual([[SET, false, [1, 2, 3]]]);
    });

    test("serializes CREATE command with record changes", () => {
        const commands = [[CREATE, "virtual_1"]];
        const params = makeParams({
            getRecord: (id) => ({ resId: false }),
            getRecordChanges: () => ({ name: "New Record" }),
        });
        const result = serializeCommands(commands, params);
        expect(result).toEqual([[CREATE, "virtual_1", { name: "New Record" }]]);
    });

    test("converts CREATE to LINK when record has resId", () => {
        const commands = [[CREATE, "virtual_1"]];
        const params = makeParams({
            getRecord: () => ({ resId: 42 }),
            getRecordChanges: () => ({}),
        });
        const result = serializeCommands(commands, params);
        expect(result).toEqual([[LINK, 42]]);
    });

    test("serializes UPDATE command with record changes", () => {
        const commands = [[UPDATE, 1]];
        const params = makeParams({
            getRecord: () => ({ resId: 1 }),
            getRecordChanges: () => ({ name: "Updated" }),
        });
        const result = serializeCommands(commands, params);
        expect(result).toEqual([[UPDATE, 1, { name: "Updated" }]]);
    });

    test("skips UPDATE with empty changes", () => {
        const commands = [[UPDATE, 1]];
        const params = makeParams({
            getRecord: () => ({ resId: 1 }),
            getRecordChanges: () => ({}),
        });
        const result = serializeCommands(commands, params);
        expect(result).toEqual([]);
    });

    test("always includes CREATE even with empty changes", () => {
        const commands = [[CREATE, "virtual_1"]];
        const params = makeParams({
            getRecord: () => ({ resId: false }),
            getRecordChanges: () => ({}),
        });
        const result = serializeCommands(commands, params);
        expect(result).toEqual([[CREATE, "virtual_1", {}]]);
    });

    test("handles unknown record commands via convertUnityValues", () => {
        const commands = [[UPDATE, 99]];
        const params = makeParams({
            unknownRecordCommands: {
                99: [[UPDATE, 99, { name: "unity_value" }]],
            },
            convertUnityValues: (values) => ({
                name: `converted_${values.name}`,
            }),
        });
        const result = serializeCommands(commands, params);
        expect(result).toEqual([[UPDATE, 99, { name: "converted_unity_value" }]]);
    });

    test("handles multiple unknown record commands for same id", () => {
        const commands = [[UPDATE, 99]];
        const params = makeParams({
            unknownRecordCommands: {
                99: [
                    [UPDATE, 99, { name: "first" }],
                    [UPDATE, 99, { name: "second" }],
                ],
            },
            convertUnityValues: (v) => v,
        });
        const result = serializeCommands(commands, params);
        expect(result.length).toBe(2);
    });

    test("handles mixed command types", () => {
        const commands = [
            [CREATE, "v1"],
            [UPDATE, 1],
            [DELETE, 2],
            [LINK, 3],
        ];
        const params = makeParams({
            getRecord: (id) => {
                if (id === "v1") {
                    return { resId: false };
                }
                return { resId: id };
            },
            getRecordChanges: (record) => {
                if (!record.resId) {
                    return { name: "new" };
                }
                return { name: "updated" };
            },
        });
        const result = serializeCommands(commands, params);
        expect(result.length).toBe(4);
        expect(result[0][0]).toBe(CREATE);
        expect(result[1][0]).toBe(UPDATE);
        expect(result[2][0]).toBe(DELETE);
        expect(result[3][0]).toBe(LINK);
    });
});

// ---------------------------------------------------------------------------
// shouldEmitDelete
// ---------------------------------------------------------------------------

describe("shouldEmitDelete", () => {
    test("returns true when no CREATE exists (real record)", () => {
        const ownCommands = [{ command: [UPDATE, 1], index: 0 }];
        expect(shouldEmitDelete(ownCommands)).toBe(true);
        // Should clear all commands
        expect(ownCommands.length).toBe(0);
    });

    test("returns false when CREATE exists (cancels out)", () => {
        const ownCommands = [
            { command: [CREATE, "v1"], index: 0 },
            { command: [UPDATE, "v1"], index: 1 },
        ];
        expect(shouldEmitDelete(ownCommands)).toBe(false);
        expect(ownCommands.length).toBe(0);
    });

    test("clears commands even when returning true", () => {
        const ownCommands = [
            { command: [UPDATE, 5], index: 0 },
            { command: [UPDATE, 5], index: 1 },
        ];
        shouldEmitDelete(ownCommands);
        expect(ownCommands.length).toBe(0);
    });

    test("handles empty command list", () => {
        const ownCommands = [];
        expect(shouldEmitDelete(ownCommands)).toBe(true);
    });
});

// ---------------------------------------------------------------------------
// shouldEmitUnlink
// ---------------------------------------------------------------------------

describe("shouldEmitUnlink", () => {
    test("returns true when no LINK exists", () => {
        const ownCommands = [{ command: [UPDATE, 3], index: 0 }];
        expect(shouldEmitUnlink(ownCommands)).toBe(true);
        expect(ownCommands.length).toBe(1); // UPDATE not removed
    });

    test("returns false when LINK exists (cancels out)", () => {
        const ownCommands = [
            { command: [LINK, 3], index: 0 },
            { command: [UPDATE, 3], index: 1 },
        ];
        expect(shouldEmitUnlink(ownCommands)).toBe(false);
        // LINK removed, UPDATE remains
        expect(ownCommands.length).toBe(1);
        expect(ownCommands[0].command[0]).toBe(UPDATE);
    });

    test("handles empty command list", () => {
        const ownCommands = [];
        expect(shouldEmitUnlink(ownCommands)).toBe(true);
    });

    test("only removes first LINK", () => {
        const ownCommands = [
            { command: [LINK, 3], index: 0 },
            { command: [LINK, 3], index: 1 },
        ];
        expect(shouldEmitUnlink(ownCommands)).toBe(false);
        expect(ownCommands.length).toBe(1);
    });
});

// ---------------------------------------------------------------------------
// absorbUnlinkIntoSet
// ---------------------------------------------------------------------------

describe("absorbUnlinkIntoSet", () => {
    test("returns false when no commands exist", () => {
        expect(absorbUnlinkIntoSet([], 1)).toBe(false);
    });

    test("returns false when first command is not SET", () => {
        const commands = [[UPDATE, 1, {}]];
        expect(absorbUnlinkIntoSet(commands, 1)).toBe(false);
    });

    test("returns false when id is not in SET list", () => {
        const commands = [[SET, false, [2, 3, 4]]];
        expect(absorbUnlinkIntoSet(commands, 1)).toBe(false);
        expect(commands[0][2]).toEqual([2, 3, 4]);
    });

    test("absorbs unlink by removing id from SET list", () => {
        const commands = [[SET, false, [1, 2, 3]]];
        expect(absorbUnlinkIntoSet(commands, 2)).toBe(true);
        expect(commands[0][2]).toEqual([1, 3]);
    });

    test("handles last id in SET list", () => {
        const commands = [[SET, false, [5]]];
        expect(absorbUnlinkIntoSet(commands, 5)).toBe(true);
        expect(commands[0][2]).toEqual([]);
    });
});

// ---------------------------------------------------------------------------
// isUpdateRedundant
// ---------------------------------------------------------------------------

describe("isUpdateRedundant", () => {
    test("returns false for empty commands", () => {
        expect(isUpdateRedundant([])).toBe(false);
    });

    test("returns true when CREATE exists", () => {
        const commands = [{ command: [CREATE, "v1"], index: 0 }];
        expect(isUpdateRedundant(commands)).toBe(true);
    });

    test("returns true when UPDATE exists", () => {
        const commands = [{ command: [UPDATE, 1], index: 0 }];
        expect(isUpdateRedundant(commands)).toBe(true);
    });

    test("returns false when only non-CREATE/UPDATE commands exist", () => {
        const commands = [
            { command: [LINK, 1], index: 0 },
            { command: [DELETE, 2], index: 1 },
        ];
        expect(isUpdateRedundant(commands)).toBe(false);
    });
});
