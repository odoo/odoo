/** @odoo-module **/
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { describe, expect, test } from "@odoo/hoot";
import { stores } from "@odoo/o-spreadsheet";
import { addGlobalFilter } from "@spreadsheet/../tests/helpers/commands";
import { makeStore } from "@spreadsheet/../tests/helpers/stores";

describe.current.tags("headless");
defineSpreadsheetModels();

const { CellComposerStore } = stores;

test("ODOO.FILTER.VALUE", async function () {
    const { store: composer, model } = await makeStore(CellComposerStore);
    await addGlobalFilter(model, {
        label: "filter 1",
        id: "42",
        type: "relation",
        defaultValue: [41],
    });
    await addGlobalFilter(model, {
        label: "filter 2",
        id: "43",
        type: "relation",
        defaultValue: [41],
    });
    for (const formula of [
        "=ODOO.FILTER.VALUE(",
        '=ODOO.FILTER.VALUE("',
        '=ODOO.FILTER.VALUE("fil',
        "=ODOO.FILTER.VALUE(fil",
    ]) {
        composer.startEdition(formula);
        const autoComplete = composer.autocompleteProvider;
        expect(autoComplete.proposals).toEqual(
            [
                {
                    htmlContent: [{ color: "#00a82d", value: '"filter 1"' }],
                    text: '"filter 1"',
                },
                {
                    htmlContent: [{ color: "#00a82d", value: '"filter 2"' }],
                    text: '"filter 2"',
                },
            ],
            { message: `autocomplete proposals for ${formula}` }
        );
        autoComplete.selectProposal(autoComplete.proposals[0].text);
        expect(composer.currentContent).toBe('=ODOO.FILTER.VALUE("filter 1"');
        expect(composer.autocompleteProvider).toBe(undefined, { message: "autocomplete closed" });
        composer.cancelEdition();
    }
});

test("escape double quotes in filter name", async function () {
    const { store: composer, model } = await makeStore(CellComposerStore);
    await addGlobalFilter(model, {
        label: 'my "special" filter',
        id: "42",
        type: "relation",
        defaultValue: [41],
    });
    composer.startEdition("=ODOO.FILTER.VALUE(");
    const autoComplete = composer.autocompleteProvider;
    expect(autoComplete.proposals[0]).toEqual({
        htmlContent: [{ color: "#00a82d", value: '"my \\"special\\" filter"' }],
        text: '"my \\"special\\" filter"',
    });
    autoComplete.selectProposal(autoComplete.proposals[0].text);
});
