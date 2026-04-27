import { SpreadsheetModels, defineSpreadsheetModels, getBasicServerData } from "@spreadsheet/../tests/helpers/data";
import {
    mockFetchSpreadsheetHistory,
    mockJoinSpreadsheetSession,
} from "@spreadsheet_edition/../tests/helpers/mock_server";
import { fields, models } from "@web/../tests/web_test_helpers";

export class SpreadsheetTest extends models.Model {
    _name = "spreadsheet.test";

    name = fields.Char({ string: "Name" });
    thumbnail = fields.Binary({ string: "Thumbnail" });
    display_thumbnail = fields.Binary({ string: "Thumbnail" });
    spreadsheet_data = fields.Text({ string: "Data" });

    join_spreadsheet_session(resId, shareId, accessToken) {
        return mockJoinSpreadsheetSession("spreadsheet.test").call(
            this,
            resId,
            shareId,
            accessToken
        );
    }

    get_spreadsheet_history(resId, fromSnapshot) {
        return mockFetchSpreadsheetHistory("spreadsheet.test").call(this, resId, fromSnapshot);
    }

    dispatch_spreadsheet_message() {
        return false;
    }
}

export class SpreadsheetCellThread extends models.Model {
    _name = "spreadsheet.cell.thread";

    dummy_id = fields.Many2one({ string: "Dummy", relation: "spreadsheet.test" });
}

export function defineTestSpreadsheetEditionModels() {
    const SpreadsheetEditionModels = { SpreadsheetCellThread, SpreadsheetTest };
    Object.assign(SpreadsheetModels, SpreadsheetEditionModels);
    defineSpreadsheetModels();
}

export function getDummyBasicServerData() {
    const { views, models } = getBasicServerData();
    return {
        views,
        models: {
            ...models,
            "spreadsheet.test": {},
            "spreadsheet.cell.thread": {},
        },
    };
}
