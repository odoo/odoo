/* eslint { "no-restricted-syntax": [ "error", {
    "selector": "MemberExpression[object.type=ThisExpression][property.name=pos]",
    "message": "Using this.pos in models is deprecated and about to be removed, for any question ask PoS team." }]}*/

import { registry } from "@web/core/registry";
import { Base } from "@point_of_sale/app/models/related_models";

export class RestaurantTable extends Base {
    static pythonModel = "restaurant.table";

    setup(vals) {
        super.setup(vals);

        this.uiState = {
            orderCount: 0,
            changeCount: 0,
            skipCount: 0,
        };
    }
}

registry.category("pos_available_models").add(RestaurantTable.pythonModel, RestaurantTable);
