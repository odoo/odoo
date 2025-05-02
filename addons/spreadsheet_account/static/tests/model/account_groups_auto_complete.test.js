import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { stores } from "@odoo/o-spreadsheet";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { makeStore } from "@spreadsheet/../tests/helpers/stores";

describe.current.tags("headless");
defineSpreadsheetModels();

const { CellComposerStore } = stores;

test("ODOO.ACCOUNT.GROUP type", async function () {
    const { store: composer } = await makeStore(CellComposerStore);

    composer.startEdition("=ODOO.ACCOUNT.GROUP(");
    await animationFrame();
    const proposals = composer.autoCompleteProposals;
    expect(proposals.map((p) => p.text)).toEqual([
        '"asset_receivable"',
        '"asset_cash"',
        '"asset_current"',
        '"asset_non_current"',
        '"asset_prepayments"',
        '"asset_fixed"',
        '"liability_payable"',
        '"liability_credit_card"',
        '"liability_current"',
        '"liability_non_current"',
        '"equity"',
        '"equity_unaffected"',
        '"income"',
        '"income_other"',
        '"expense"',
        '"expense_depreciation"',
        '"expense_direct_cost"',
        '"off_balance"',
    ]);
    composer.insertAutoCompleteValue(proposals[0].text);
    await animationFrame();
    expect(composer.currentContent).toBe('=ODOO.ACCOUNT.GROUP("asset_receivable"');
    expect(composer.isAutoCompleteDisplayed).toBe(false);
});
