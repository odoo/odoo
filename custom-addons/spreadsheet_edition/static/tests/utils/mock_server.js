/** @odoo-module */

import { RPCError } from "@web/core/network/rpc_service";

export function mockJoinSpreadsheetSession(resModel) {
    return function (route, args) {
        const [id] = args.args;
        const record = this.models[resModel].records.find((record) => record.id === id);
        if (!record) {
            const error = new RPCError(`Spreadsheet ${id} does not exist`);
            error.data = {};
            throw error;
        }
        return {
            data: JSON.parse(record.spreadsheet_data),
            name: record.name,
            revisions: [],
            isReadonly: false,
        };
    };
}

export function mockFetchSpreadsheetHistory(resModel) {
    return function (route, args) {
        const [id] = args.args;
        const record = this.models[resModel].records.find((record) => record.id === id);
        if (!record) {
            throw new Error(`Spreadsheet ${id} does not exist`);
        }
        return {
            name: record.name,
            data: JSON.parse(record.spreadsheet_data),
            revisions: [],
        };
    };
}
