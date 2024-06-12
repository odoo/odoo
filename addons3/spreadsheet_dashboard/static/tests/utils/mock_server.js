/** @odoo-module */

import { RPCError } from "@web/core/network/rpc_service";
import { registry } from "@web/core/registry";

registry
    .category("mock_server")
    .add("spreadsheet.dashboard/get_readonly_dashboard", function (route, args) {
        const [id] = args.args;
        const dashboard = this.models["spreadsheet.dashboard"].records.find(
            (record) => record.id === id
        );
        if (!dashboard) {
            const error = new RPCError();
            error.data = {};
            throw error;
        }
        return {
            snapshot: JSON.parse(dashboard.spreadsheet_data),
            revisions: [],
        };
    });
