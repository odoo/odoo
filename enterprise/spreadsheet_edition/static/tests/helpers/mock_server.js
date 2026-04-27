import { RPCError } from "@web/core/network/rpc";

export function mockJoinSpreadsheetSession(resModel) {
    return function (resId, accessToken) {
        const record = this.env[resModel].search_read([["id", "=", resId]])[0];
        if (!record) {
            const error = new RPCError(`Spreadsheet ${resId} does not exist`);
            error.data = {};
            throw error;
        }
        return {
            data: JSON.parse(record.spreadsheet_data),
            name: record.name,
            revisions: [],
            isReadonly: false,
            writable_rec_name_field: "name",
        };
    };
}

export function mockFetchSpreadsheetHistory(resModel) {
    return function (resId, fromSnapshot = false) {
        const record = this.env[resModel].search_read([["id", "=", resId]])[0];
        if (!record) {
            throw new Error(`Spreadsheet ${resId} does not exist`);
        }
        return {
            name: record.name,
            data: JSON.parse(record.spreadsheet_data),
            revisions: [],
        };
    };
}
