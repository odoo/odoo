/** @odoo-module */

import { registry } from "@web/core/registry";
import { mockJoinSpreadsheetSession, mockFetchSpreadsheetHistory } from "@spreadsheet_edition/../tests/utils/mock_server";

registry
    .category("mock_server")
    .add(
        "spreadsheet.test/join_spreadsheet_session", mockJoinSpreadsheetSession("spreadsheet.test")
    );
registry
    .category("mock_server")
    .add(
        "spreadsheet.test/get_spreadsheet_history", mockFetchSpreadsheetHistory("spreadsheet.test")
    );
