/** @odoo-module */

import { registry } from "@web/core/registry";
import { mockJoinSpreadsheetSession } from "@spreadsheet_edition/../tests/utils/mock_server";

registry
    .category("mock_server")
    .add("documents.document/get_spreadsheets_to_display", function () {
        return this.models["documents.document"].records
            .filter((document) => document.handler === "spreadsheet")
            .map((spreadsheet) => ({
                name: spreadsheet.name,
                id: spreadsheet.id,
            }));
    })
    .add("documents.document/join_spreadsheet_session", function (route, args) {
        const result = mockJoinSpreadsheetSession("documents.document").call(this, route, args);
        const [id] = args.args;
        const record = this.models["documents.document"].records.find((record) => record.id === id);
        result.is_favorited = record.is_favorited;
        result.folder_id = record.folder_id;
        return result;
    })
    .add("documents.document/dispatch_spreadsheet_message", () => false)
    .add("documents.document/action_open_new_spreadsheet", function (route, args) {
        const spreadsheetId = this.mockCreate("documents.document", {
            name: "Untitled spreadsheet",
            mimetype: "application/o-spreadsheet",
            spreadsheet_data: "{}",
            handler: "spreadsheet",
        });
        return {
            type: "ir.actions.client",
            tag: "action_open_spreadsheet",
            params: {
                spreadsheet_id: spreadsheetId,
                is_new_spreadsheet: true,
            },
        };
    })
    .add("spreadsheet.template/fetch_template_data", function (route, args) {
        const [id] = args.args;
        const record = this.models["spreadsheet.template"].records.find(
            (record) => record.id === id
        );
        if (!record) {
            throw new Error(`Spreadsheet Template ${id} does not exist`);
        }
        return {
            data:
                typeof record.spreadsheet_data === "string"
                    ? JSON.parse(record.spreadsheet_data)
                    : record.spreadsheet_data,
            name: record.name,
            isReadonly: false,
        };
    })
    .add(
        "spreadsheet.template/join_spreadsheet_session",
        mockJoinSpreadsheetSession("spreadsheet.template")
    );
