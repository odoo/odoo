import {
    SpreadsheetModels,
    defineSpreadsheetModels,
    getBasicData,
} from "@spreadsheet/../tests/helpers/data";
import { fields, models } from "@web/../tests/web_test_helpers";

export class AccountMoveLine extends models.Model {
    _name = "account.move.line";

    account_id = fields.Many2one({ relation: "account.account" });
    date = fields.Date({ string: "Date" });
    name = fields.Char({ string: "Name" });

    _records = [
        { id: 1, name: "line1", account_id: 1, date: "2022-06-01" },
        { id: 2, name: "line2", account_id: 2, date: "2022-06-23" },
    ];
}

export class AccountAccount extends models.Model {
    _name = "account.account";

    code = fields.Char({ string: "Code" });
    account_type = fields.Char({ string: "Account type" });

    spreadsheet_fetch_debit_credit(args) {
        return new Array(args.length).fill({ credit: 0, debit: 0 });
    }

    get_account_group(accountTypes) {
        const data = accountTypes.map((accountType) => {
            const records = this.env["account.account"].search_read(
                [["account_type", "=", accountType]],
                ["code"]
            );
            return records.map((record) => record.code);
        });
        return data;
    }

    _records = [
        { id: 1, code: "100104", account_type: "income" },
        { id: 2, code: "100105", account_type: "income_other" },
        { id: 3, code: "200104", account_type: "income" },
    ];
}

export function getAccountingData() {
    return {
        models: { ...getBasicData() },
        views: {
            "account.move.line,false,list": /* xml */ `
                    <list string="Move Lines">
                        <field name="id"/>
                        <field name="account_id"/>
                        <field name="date"/>
                    </list>
                `,
        },
    };
}

export function defineSpreadsheetAccountModels() {
    const SpreadsheetAccountModels = [AccountMoveLine, AccountAccount];
    Object.assign(SpreadsheetModels, SpreadsheetAccountModels);
    defineSpreadsheetModels();
}
