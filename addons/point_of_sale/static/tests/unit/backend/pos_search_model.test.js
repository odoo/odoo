import { expect, test, describe } from "@odoo/hoot";
import { mountWithSearch } from "@web/../tests/web_test_helpers";
import { definePosModels } from "../data/generate_model_definitions";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { PosSearchModel } from "@point_of_sale/backend/views/pos_search_model";

definePosModels();

describe("SearchModel", () => {
    test("pos orders can be grouped by hour", async () => {
        odoo.pos_session_id = 1;
        odoo.pos_config_id = 1;
        odoo.info = {
            db: "pos",
            isEnterprise: true,
        };
        const component = await mountWithSearch(SearchBar, {
            resModel: "pos.order",
            searchMenuTypes: ["groupBy"],
            SearchModel: PosSearchModel,
            searchViewId: false,
            searchViewFields: {
                date_order: {
                    string: "Order Date",
                    type: "datetime",
                    store: true,
                    sortable: true,
                    groupable: true,
                },
            },
            searchViewArch: `
            <search>
                <filter name="date_groupBy" string="Date Order" context="{'group_by': 'date_order:hour'}"/>
            </search>
        `,
        });

        const filterId = Object.keys(component.env.searchModel.searchItems).map((key) =>
            Number(key)
        )[0];
        component.env.searchModel.toggleDateGroupBy(filterId);
        expect(component.env.searchModel.groupBy).toEqual(["date_order:hour"]);
        component.env.searchModel.toggleDateGroupBy(filterId, "day");
        expect(component.env.searchModel.groupBy).toEqual(["date_order:day", "date_order:hour"]);
        component.env.searchModel.toggleDateGroupBy(filterId, "hour");
        expect(component.env.searchModel.groupBy).toEqual(["date_order:day"]);
    });
});
