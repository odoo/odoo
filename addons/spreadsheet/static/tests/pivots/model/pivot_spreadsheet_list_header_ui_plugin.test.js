import { describe, expect, test } from "@odoo/hoot";
import {
    defineSpreadsheetActions,
    defineSpreadsheetModels,
} from "@spreadsheet/../tests/helpers/data";
import { setSelection, updatePivot } from "@spreadsheet/../tests/helpers/commands";
import { createSpreadsheetWithList } from "@spreadsheet/../tests/helpers/list";
import { serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("headless");
defineSpreadsheetModels();
defineSpreadsheetActions();

function addSpreadsheetPivot(model, zoneXc, pivotId = "PIVOT#1") {
    setSelection(model, zoneXc);
    const result = model.dispatch("ADD_PIVOT", {
        pivotId,
        pivot: {
            name: "Pivot",
            type: "SPREADSHEET",
            dataSet: {
                zone: model.getters.getSelectedZone(),
                sheetId: model.getters.getActiveSheetId(),
            },
            rows: [],
            columns: [],
            measures: [],
        },
    });
    expect(result.isSuccessful).toBe(true);
}

function updateSpreadsheetPivotRange(model, pivotId, zoneXc) {
    setSelection(model, zoneXc);
    const result = updatePivot(model, pivotId, {
        dataSet: {
            zone: model.getters.getSelectedZone(),
            sheetId: model.getters.getActiveSheetId(),
        },
    });
    expect(result.isSuccessful).toBe(true);
}

function captureNotifications(model) {
    const notifications = [];
    model.on("notify-ui", {}, (notification) => notifications.push(notification));
    return notifications;
}

function getListColumn(model, fieldName) {
    const [listId] = model.getters.getListIds();
    return model.getters
        .getListDefinition(listId)
        .columns.find((column) => column.name === fieldName);
}

test("spreadsheet pivots lock only list headers without explicit labels", async () => {
    serverState.multiLang = true;

    const { model } = await createSpreadsheetWithList({
        columns: [
            { name: "foo" },
            { name: "bar", string: "Bar" },
            { name: "date", string: "Custom Date" },
            { name: "product_id" },
        ],
    });
    const notifications = captureNotifications(model);

    addSpreadsheetPivot(model, "A1:C5");

    expect(getListColumn(model, "foo")).toEqual({
        name: "foo",
        string: "Foo",
    });
    expect(getListColumn(model, "bar")).toEqual({
        name: "bar",
        string: "Bar",
    });
    expect(getListColumn(model, "date")).toEqual({
        name: "date",
        string: "Custom Date",
    });
    expect(getListColumn(model, "product_id")).toEqual({
        name: "product_id",
    });

    expect(notifications).toEqual([
        {
            type: "info",
            sticky: false,
            text: "Some list column titles have been locked to avoid translation issues.",
        },
    ]);
});

test("spreadsheet pivots do not lock list headers when multi-language support is disabled", async () => {
    serverState.multiLang = false;

    const { model } = await createSpreadsheetWithList({
        columns: [{ name: "foo" }, { name: "bar" }],
    });
    const notifications = captureNotifications(model);

    addSpreadsheetPivot(model, "A1:B5");

    expect(getListColumn(model, "foo")).toEqual({
        name: "foo",
    });
    expect(getListColumn(model, "bar")).toEqual({
        name: "bar",
    });
    expect(notifications).toEqual([]);
});

test("spreadsheet pivots do not lock or notify when selected headers already have explicit labels", async () => {
    serverState.multiLang = true;

    const { model } = await createSpreadsheetWithList({
        columns: [
            { name: "foo", string: "Foo" },
            { name: "bar", string: "Custom Bar" },
        ],
    });
    const notifications = captureNotifications(model);

    addSpreadsheetPivot(model, "A1:B5");

    expect(getListColumn(model, "foo")).toEqual({
        name: "foo",
        string: "Foo",
    });
    expect(getListColumn(model, "bar")).toEqual({
        name: "bar",
        string: "Custom Bar",
    });
    expect(notifications).toEqual([]);
});

test("updating a spreadsheet pivot range locks newly used list headers without explicit labels", async () => {
    serverState.multiLang = true;

    const { model } = await createSpreadsheetWithList({
        columns: [{ name: "foo" }, { name: "bar" }],
    });
    const notifications = captureNotifications(model);

    addSpreadsheetPivot(model, "A1:A5");
    updateSpreadsheetPivotRange(model, "PIVOT#1", "A1:B5");

    expect(getListColumn(model, "foo")).toEqual({
        name: "foo",
        string: "Foo",
    });
    expect(getListColumn(model, "bar")).toEqual({
        name: "bar",
        string: "Bar",
    });
    expect(notifications).toEqual([
        {
            type: "info",
            sticky: false,
            text: "Some list column titles have been locked to avoid translation issues.",
        },
        {
            type: "info",
            sticky: false,
            text: "Some list column titles have been locked to avoid translation issues.",
        },
    ]);
});
