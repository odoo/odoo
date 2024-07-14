/** @odoo-module */

import { registry } from "@web/core/registry";
import { mockJoinSpreadsheetSession } from "@spreadsheet_edition/../tests/utils/mock_server";

registry
    .category("mock_server")
    .add(
        "spreadsheet.dashboard/join_spreadsheet_session",
        mockJoinSpreadsheetSession("spreadsheet.dashboard")
    );
