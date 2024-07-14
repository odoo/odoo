/** @odoo-module */
import { getBasicServerData } from "@spreadsheet/../tests/utils/data";

export function getDashboardBasicServerData() {
    const { views, models } = getBasicServerData();
    return {
        views,
        models: {
            ...models,
            "spreadsheet.dashboard": {
                fields: {
                    name: { string: "Name", type: "char" },
                    spreadsheet_data: { string: "Data", type: "text" },
                    thumbnail: { string: "Thumbnail", type: "text" },
                    data: { string: "base64 encoded data", type: "text" },
                },
                records: [],
            },
        },
    };
}
