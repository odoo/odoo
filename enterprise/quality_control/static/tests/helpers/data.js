import { defineModels, fields } from "@web/../tests/web_test_helpers";
import { SpreadsheetMixin } from "@spreadsheet/../tests/helpers/data";
import { mockJoinSpreadsheetSession } from "@spreadsheet_edition/../tests/helpers/mock_server";


class QualityCheckSpreadsheet extends SpreadsheetMixin {
    _name = "quality.check.spreadsheet";

    name = fields.Char();
    check_cell = fields.Char();

    _records = [
        {
            id: 1,
            name: "My quality check spreadsheet",
            spreadsheet_data: "{}",
            check_cell: "A1"
        },
        {
            id: 1111,
            name: "My quality check spreadsheet",
            spreadsheet_data: "{}",
            check_cell: "A1"
        },
    ];

    join_spreadsheet_session(resId, shareId, accessToken) {
        const result = mockJoinSpreadsheetSession(this._name).call(
            this,
            resId,
            shareId,
            accessToken
        );
        result.quality_check_display_name = "The check name";
        result.quality_check_cell = this[0].check_cell;
        return result;
    }

    dispatch_spreadsheet_message() {}
}

export function defineQualitySpreadsheetModels() {
    defineModels({
        QualityCheckSpreadsheet,
    });
}
