/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    async _performRPC(route, args) {
        if (args.method === "grid_update_cell") {
            return this.mockGridUpdateCell(args.model, args.args, args.kwargs);
        }
        return super._performRPC(...arguments);
    },

    mockGridUpdateCell(modelName, args, kwargs) {
        const [domain, fieldNameToUpdate, value] = args;
        const recordsFetched = this.mockSearchRead(
            modelName,
            [domain, [fieldNameToUpdate]],
            kwargs
        );
        if (recordsFetched.length > 1) {
            this.mockCopy(modelName, [recordsFetched[0].id, { [fieldNameToUpdate]: value }]);
        } else if (recordsFetched.length === 1) {
            const record = recordsFetched[0];
            this.mockWrite(modelName, [
                [record.id],
                { [fieldNameToUpdate]: record[fieldNameToUpdate] + value },
            ]);
        } else {
            this.mockCreate(modelName, { [fieldNameToUpdate]: value }, kwargs);
        }
    },
});
