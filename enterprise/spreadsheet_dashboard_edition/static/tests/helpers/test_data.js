import {
    SpreadsheetModels,
    defineSpreadsheetModels,
    getBasicServerData,
} from "@spreadsheet/../tests/helpers/data";
import {
    SpreadsheetDashboard as SpreadsheetDashboardCommunity,
    SpreadsheetDashboardGroup as SpreadsheetDashboardGroupCommunity,
} from "@spreadsheet_dashboard/../tests/helpers/data";
import { mockJoinSpreadsheetSession } from "@spreadsheet_edition/../tests/helpers/mock_server";

export class SpreadsheetDashboard extends SpreadsheetDashboardCommunity {
    join_spreadsheet_session(resId, shareId, accessTokens) {
        return mockJoinSpreadsheetSession("spreadsheet.dashboard").call(
            this,
            resId,
            shareId,
            accessTokens
        );
    }

    _records = [];
}

export class SpreadsheetDashboardGroup extends SpreadsheetDashboardGroupCommunity {
    _records = [];
}

export function defineSpreadsheetDashboardEditionModels() {
    const SpreadsheetDashboardModels = [SpreadsheetDashboard, SpreadsheetDashboardGroup];
    Object.assign(SpreadsheetModels, SpreadsheetDashboardModels);
    defineSpreadsheetModels();
}

export function getDashboardBasicServerData() {
    const { views, models } = getBasicServerData();
    return { views, models: { ...models, "spreadsheet.dashboard": {} } };
}
