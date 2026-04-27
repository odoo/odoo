import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { stores } from "@odoo/o-spreadsheet";
import { Partner, defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { insertListInSpreadsheet } from "@spreadsheet/../tests/helpers/list";
import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";
import { makeStore, makeStoreWithModel } from "@spreadsheet/../tests/helpers/stores";

describe.current.tags("headless");
defineSpreadsheetModels();

const { CellComposerStore } = stores;

test("ODOO.LIST id", async function () {
    const { store: composer, model } = await makeStore(CellComposerStore);
    insertListInSpreadsheet(model, {
        model: "partner",
        columns: ["foo", "bar", "date", "product_id"],
    });
    await animationFrame();
    for (const formula of ["=ODOO.LIST(", "=ODOO.LIST( ", "=ODOO.LIST.HEADER("]) {
        composer.startEdition(formula);
        const autoComplete = composer.autocompleteProvider;
        expect(autoComplete.proposals).toEqual([
            {
                description: "List",
                fuzzySearchKey: "1List",
                htmlContent: [{ color: "#02c39a", value: "1" }],
                text: "1",
            },
        ]);
        composer.cancelEdition();
    }
});

test("ODOO.LIST id exact match", async function () {
    const { store: composer, model } = await makeStore(CellComposerStore);
    insertListInSpreadsheet(model, {
        model: "partner",
        columns: ["foo", "bar", "date", "product_id"],
    });
    await animationFrame();
    composer.startEdition("=ODOO.LIST(1");
    const autoComplete = composer.autocompleteProvider;
    expect(autoComplete).toBe(undefined);
});

test("ODOO.LIST field name", async function () {
    const model = await createModelWithDataSource();
    const { store: composer } = await makeStoreWithModel(model, CellComposerStore);
    insertListInSpreadsheet(model, {
        model: "partner",
        columns: ["product_id", "bar"],
    });
    await animationFrame();
    composer.startEdition("=ODOO.LIST(1,1,");
    const autoComplete = composer.autocompleteProvider;
    const allFields = Object.keys(Partner._fields);
    expect(autoComplete.proposals.map((p) => p.text)).toEqual(
        allFields.map((field) => `"${field}"`),
        { message: "all fields are proposed, quoted" }
    );
    // check completely only the first one
    expect(autoComplete.proposals[0]).toEqual({
        description: "Id",
        fuzzySearchKey: 'Id"id"',
        htmlContent: [{ color: "#00a82d", value: '"id"' }],
        text: '"id"',
    });
    autoComplete.selectProposal(autoComplete.proposals[0].text);
    expect(composer.currentContent).toBe('=ODOO.LIST(1,1,"id"');
    expect(composer.autocompleteProvider).toBe(undefined, { message: "autocomplete closed" });
});

test("ODOO.LIST.HEADER field name", async function () {
    const model = await createModelWithDataSource();
    const { store: composer } = await makeStoreWithModel(model, CellComposerStore);
    insertListInSpreadsheet(model, {
        model: "partner",
        columns: ["product_id", "bar"],
    });
    await animationFrame();
    composer.startEdition("=ODOO.LIST.HEADER(1,");
    const autoComplete = composer.autocompleteProvider;
    const allFields = Object.keys(Partner._fields);
    expect(autoComplete.proposals.map((p) => p.text)).toEqual(
        allFields.map((field) => `"${field}"`),
        { message: "all fields are proposed, quoted" }
    );
});

test("ODOO.LIST field name with invalid list id", async function () {
    const { store: composer, model } = await makeStore(CellComposerStore);
    insertListInSpreadsheet(model, {
        model: "partner",
        columns: ["foo", "bar", "date", "product_id"],
    });
    await animationFrame();
    for (const listId of ["", "0", "42"]) {
        composer.startEdition(`=ODOO.LIST(${listId},1,`);
        const autoComplete = composer.autocompleteProvider;
        expect(autoComplete).toBe(undefined);
        composer.cancelEdition();
    }
});
