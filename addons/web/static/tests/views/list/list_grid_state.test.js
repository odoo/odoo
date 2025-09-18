// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { ListGridState } from "@web/views/list/list_grid_state";

describe.current.tags("headless");

// ---------------------------------------------------------------------------
// Mock helpers
// ---------------------------------------------------------------------------

function mockRecord(id) {
    return { id: String(id), resId: id, selected: false };
}

function mockColumn(name, type = "field", readonly = false) {
    return { id: `col_${name}`, name, type, readonly };
}

function mockGroup(id, records, isFolded = false, subGroups = null) {
    const list = {
        records,
        isGrouped: Boolean(subGroups),
        groups: subGroups || [],
    };
    return {
        id: String(id),
        isFolded,
        displayName: `Group ${id}`,
        list,
    };
}

function mockList(records, groups = null) {
    return {
        records: groups ? [] : records,
        isGrouped: Boolean(groups),
        groups: groups || [],
    };
}

function makeGridState(options = {}) {
    const records = options.records || [1, 2, 3, 4, 5].map(mockRecord);
    const columns = options.columns || [
        mockColumn("name"),
        mockColumn("email"),
        mockColumn("phone"),
    ];
    const list = options.list || mockList(records);
    return new ListGridState({
        list,
        columns,
        hasSelectors: options.hasSelectors ?? false,
        hasOpenFormViewColumn: options.hasOpenFormViewColumn ?? false,
        hasActionsColumn: options.hasActionsColumn ?? false,
        isRTL: options.isRTL ?? false,
        showAddLine: options.showAddLine ?? false,
        isCellReadonly: options.isCellReadonly ?? (() => false),
    });
}

// ---------------------------------------------------------------------------
// Flat row materialization
// ---------------------------------------------------------------------------

describe("flat row materialization", () => {
    test("ungrouped: 5 records produce 5 flat rows of type 'record'", () => {
        const gs = makeGridState();
        expect(gs.rowCount).toBe(5);
        expect(gs.flatRows.every((r) => r.type === "record")).toBe(true);
        expect(gs.flatRows.map((r) => r.globalIndex)).toEqual([0, 1, 2, 3, 4]);
        expect(gs.flatRows[0].record.id).toBe("1");
        expect(gs.flatRows[4].record.id).toBe("5");
    });

    test("grouped: 2 open groups with records produce correct interleaving", () => {
        const records1 = [1, 2, 3].map(mockRecord);
        const records2 = [4, 5].map(mockRecord);
        const groups = [mockGroup(10, records1), mockGroup(20, records2)];
        const list = mockList([], groups);
        const gs = makeGridState({ list, showAddLine: true });

        // group1 header, 3 records, add-line, group2 header, 2 records, add-line
        expect(gs.rowCount).toBe(9);
        expect(gs.flatRows[0].type).toBe("group");
        expect(gs.flatRows[0].group.id).toBe("10");
        expect(gs.flatRows[1].type).toBe("record");
        expect(gs.flatRows[1].record.id).toBe("1");
        expect(gs.flatRows[3].type).toBe("record");
        expect(gs.flatRows[3].record.id).toBe("3");
        expect(gs.flatRows[4].type).toBe("add-line");
        expect(gs.flatRows[5].type).toBe("group");
        expect(gs.flatRows[5].group.id).toBe("20");
        expect(gs.flatRows[6].type).toBe("record");
        expect(gs.flatRows[6].record.id).toBe("4");
        expect(gs.flatRows[7].type).toBe("record");
        expect(gs.flatRows[7].record.id).toBe("5");
        expect(gs.flatRows[8].type).toBe("add-line");
    });

    test("folded groups produce only header rows, no children", () => {
        const records = [1, 2].map(mockRecord);
        const groups = [
            mockGroup(10, records, true),
            mockGroup(20, [3].map(mockRecord)),
        ];
        const list = mockList([], groups);
        const gs = makeGridState({ list, showAddLine: true });

        // folded group header only, then open group header + 1 record + add-line
        expect(gs.rowCount).toBe(4);
        expect(gs.flatRows[0].type).toBe("group");
        expect(gs.flatRows[0].group.isFolded).toBe(true);
        expect(gs.flatRows[1].type).toBe("group");
        expect(gs.flatRows[1].group.id).toBe("20");
        expect(gs.flatRows[2].type).toBe("record");
        expect(gs.flatRows[3].type).toBe("add-line");
    });

    test("nested groups: 2 levels deep with correct depth tracking", () => {
        const innerRecords = [1, 2].map(mockRecord);
        const innerGroup = mockGroup(100, innerRecords);
        const outerGroup = mockGroup(10, [], false, [innerGroup]);
        const list = mockList([], [outerGroup]);
        const gs = makeGridState({ list, showAddLine: true });

        // outer header (depth 0), inner header (depth 1), 2 records (depth 2), add-line (depth 2)
        expect(gs.rowCount).toBe(5);
        expect(gs.flatRows[0].depth).toBe(0);
        expect(gs.flatRows[0].type).toBe("group");
        expect(gs.flatRows[1].depth).toBe(1);
        expect(gs.flatRows[1].type).toBe("group");
        expect(gs.flatRows[2].depth).toBe(2);
        expect(gs.flatRows[2].type).toBe("record");
        expect(gs.flatRows[4].depth).toBe(2);
        expect(gs.flatRows[4].type).toBe("add-line");
    });

    test("empty ungrouped list produces 0 flat rows", () => {
        const gs = makeGridState({ records: [], list: mockList([]) });
        expect(gs.rowCount).toBe(0);
    });
});

// ---------------------------------------------------------------------------
// moveFocus
// ---------------------------------------------------------------------------

describe("moveFocus", () => {
    test("up/down ungrouped: correct index arithmetic", () => {
        const gs = makeGridState();
        // Move down from row 0, col 1
        const down = gs.moveFocus(0, 1, "down");
        expect(down).toEqual({ rowIndex: 1, colIndex: 1 });

        // Move up from row 2, col 2
        const up = gs.moveFocus(2, 2, "up");
        expect(up).toEqual({ rowIndex: 1, colIndex: 2 });
    });

    test("up/down: null at boundaries", () => {
        const gs = makeGridState();
        expect(gs.moveFocus(0, 0, "up")).toBe(null);
        expect(gs.moveFocus(4, 0, "down")).toBe(null);
    });

    test("up/down grouped: cross group-to-record boundary preserves lastColIndex", () => {
        const records1 = [1, 2].map(mockRecord);
        const groups = [mockGroup(10, records1)];
        const list = mockList([], groups);
        const gs = makeGridState({ list });

        // flatRows: [group(0), record(1), record(2)]
        // Start at record row 1, col 2, move up to group header row 0
        const up = gs.moveFocus(1, 2, "up");
        expect(up).toEqual({ rowIndex: 0, colIndex: 0 }); // group is single-cell

        // Now move back down from group header to record
        const down = gs.moveFocus(0, 0, "down");
        expect(down).toEqual({ rowIndex: 1, colIndex: 2 }); // restores lastColIndex
    });

    test("left/right: correct bounds", () => {
        const gs = makeGridState(); // 3 columns, no selectors
        const right = gs.moveFocus(0, 0, "right");
        expect(right).toEqual({ rowIndex: 0, colIndex: 1 });

        const left = gs.moveFocus(0, 1, "left");
        expect(left).toEqual({ rowIndex: 0, colIndex: 0 });

        // At boundary
        expect(gs.moveFocus(0, 0, "left")).toBe(null);
        expect(gs.moveFocus(0, 2, "right")).toBe(null);
    });

    test("left/right RTL: direction is swapped", () => {
        const gs = makeGridState({ isRTL: true });
        // "right" in RTL becomes "left" internally
        const result = gs.moveFocus(0, 1, "right");
        expect(result).toEqual({ rowIndex: 0, colIndex: 0 });

        const result2 = gs.moveFocus(0, 0, "left");
        expect(result2).toEqual({ rowIndex: 0, colIndex: 1 });
    });

    test("colCount includes selector/formView/actions columns", () => {
        const gs = makeGridState({
            hasSelectors: true,
            hasOpenFormViewColumn: true,
            hasActionsColumn: true,
        });
        // 3 field columns + 3 extra = 6
        expect(gs.colCount).toBe(6);
        // Can move right to col 5
        expect(gs.moveFocus(0, 4, "right")).toEqual({ rowIndex: 0, colIndex: 5 });
        expect(gs.moveFocus(0, 5, "right")).toBe(null);
    });
});

// ---------------------------------------------------------------------------
// findNextEditableCell
// ---------------------------------------------------------------------------

describe("findNextEditableCell", () => {
    test("skips readonly columns", () => {
        const columns = [mockColumn("name"), mockColumn("email"), mockColumn("phone")];
        const gs = makeGridState({
            columns,
            isCellReadonly: (col) => col.name === "email",
        });
        // From col 0 (name), skip col 1 (email, readonly), land on col 2 (phone)
        const next = gs.findNextEditableCell(0, 0, true);
        expect(next).toEqual({ rowIndex: 0, colIndex: 2 });
    });

    test("returns null when no editable cell found", () => {
        const gs = makeGridState({ isCellReadonly: () => true });
        expect(gs.findNextEditableCell(0, 0, true)).toBe(null);
    });

    test("backward search works", () => {
        const columns = [mockColumn("name"), mockColumn("email"), mockColumn("phone")];
        const gs = makeGridState({
            columns,
            isCellReadonly: (col) => col.name === "email",
        });
        // From col 2 (phone), skip col 1 (email, readonly), land on col 0 (name)
        const prev = gs.findNextEditableCell(0, 2, false);
        expect(prev).toEqual({ rowIndex: 0, colIndex: 0 });
    });

    test("skips non-field columns", () => {
        const columns = [
            mockColumn("name"),
            mockColumn("buttons", "button_group"),
            mockColumn("phone"),
        ];
        const gs = makeGridState({ columns });
        const next = gs.findNextEditableCell(0, 0, true);
        expect(next).toEqual({ rowIndex: 0, colIndex: 2 });
    });

    test("returns null for group rows", () => {
        const groups = [mockGroup(10, [1].map(mockRecord))];
        const list = mockList([], groups);
        const gs = makeGridState({ list });
        // Row 0 is a group header
        expect(gs.findNextEditableCell(0, 0, true)).toBe(null);
    });

    test("with selectors: column indices are offset by 1", () => {
        const gs = makeGridState({ hasSelectors: true });
        // With selectors, field columns start at index 1
        // findNextEditableCell from col 1 (name) should find col 2 (email)
        const next = gs.findNextEditableCell(0, 1, true);
        expect(next).toEqual({ rowIndex: 0, colIndex: 2 });
    });
});

// ---------------------------------------------------------------------------
// isCellEditable
// ---------------------------------------------------------------------------

describe("isCellEditable", () => {
    test("returns true for editable field cells", () => {
        const gs = makeGridState();
        expect(gs.isCellEditable(0, 0)).toBe(true);
    });

    test("returns false for readonly cells", () => {
        const gs = makeGridState({ isCellReadonly: () => true });
        expect(gs.isCellEditable(0, 0)).toBe(false);
    });

    test("returns false for group rows", () => {
        const groups = [mockGroup(10, [1].map(mockRecord))];
        const list = mockList([], groups);
        const gs = makeGridState({ list });
        expect(gs.isCellEditable(0, 0)).toBe(false);
    });

    test("returns false for out-of-range indices", () => {
        const gs = makeGridState();
        expect(gs.isCellEditable(99, 0)).toBe(false);
        expect(gs.isCellEditable(0, 99)).toBe(false);
    });
});

// ---------------------------------------------------------------------------
// Reverse lookup
// ---------------------------------------------------------------------------

describe("reverse lookup", () => {
    test("findRowByRecordId returns correct flat row", () => {
        const gs = makeGridState();
        const row = gs.findRowByRecordId("3");
        expect(row).not.toBe(undefined);
        expect(row.type).toBe("record");
        expect(row.globalIndex).toBe(2);
        expect(row.record.id).toBe("3");
    });

    test("findRowByRecordId returns undefined for missing ID", () => {
        const gs = makeGridState();
        expect(gs.findRowByRecordId("999")).toBe(undefined);
    });

    test("findRowByGroupId returns correct flat row", () => {
        const groups = [mockGroup(10, [1].map(mockRecord))];
        const list = mockList([], groups);
        const gs = makeGridState({ list });

        const row = gs.findRowByGroupId("10");
        expect(row).not.toBe(undefined);
        expect(row.type).toBe("group");
        expect(row.group.id).toBe("10");
    });

    test("getColIndexByName returns correct index", () => {
        const gs = makeGridState();
        expect(gs.getColIndexByName("name")).toBe(0);
        expect(gs.getColIndexByName("email")).toBe(1);
        expect(gs.getColIndexByName("phone")).toBe(2);
        expect(gs.getColIndexByName("nonexistent")).toBe(-1);
    });

    test("getColIndexByName with selectors adds offset", () => {
        const gs = makeGridState({ hasSelectors: true });
        expect(gs.getColIndexByName("name")).toBe(1);
        expect(gs.getColIndexByName("email")).toBe(2);
    });
});

// ---------------------------------------------------------------------------
// Rebuild after structural change
// ---------------------------------------------------------------------------

describe("rebuild", () => {
    test("rebuild after group toggle changes row count", () => {
        const records = [1, 2].map(mockRecord);
        const group = mockGroup(10, records);
        const list = mockList([], [group]);
        const gs = makeGridState({ list, showAddLine: true });

        // Open: group header + 2 records + add-line = 4
        expect(gs.rowCount).toBe(4);

        // Simulate folding
        group.isFolded = true;
        gs.rebuild();

        // Folded: group header only = 1
        expect(gs.rowCount).toBe(1);
        expect(gs.flatRows[0].type).toBe("group");
    });

    test("update + rebuild refreshes with new columns", () => {
        const gs = makeGridState();
        expect(gs.colCount).toBe(3);

        gs.update({ columns: [mockColumn("name"), mockColumn("email")] });
        gs.rebuild();
        expect(gs.colCount).toBe(2);
    });

    test("rebuild preserves lookup consistency", () => {
        const records = [1, 2, 3].map(mockRecord);
        const group = mockGroup(10, records);
        const list = mockList([], [group]);
        const gs = makeGridState({ list });

        const before = gs.findRowByRecordId("2");
        expect(before.globalIndex).toBe(2);

        // Add a record and rebuild
        records.push(mockRecord(4));
        gs.rebuild();

        // Record "2" should still be findable (with same index since insertion is at end)
        const after = gs.findRowByRecordId("2");
        expect(after).not.toBe(undefined);
        expect(after.record.id).toBe("2");
    });
});
