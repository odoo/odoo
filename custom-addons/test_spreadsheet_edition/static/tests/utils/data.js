/** @odoo-module */

import { getBasicServerData } from "@spreadsheet/../tests/utils/data";

export function getDummyBasicServerData() {
    const { views, models } = getBasicServerData();
    return {
        views,
        models: {
            ...models,
            "spreadsheet.test": {
                fields: {
                    id: { string: "ID", type: "integer" },
                    name: { string: "Name", type: "char" },
                    spreadsheet_data: { string: "Data", type: "text" },
                },
                records: [],
            },
        },
    };
}
