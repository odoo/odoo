import { registry } from "@web/core/registry";
import { Base } from "@point_of_sale/app/models/related_models";

export class RestaurantFloor extends Base {
    static pythonModel = "restaurant.floor";

    get sortedTable() {
        return [...this.table_ids].sort((a, b) => a.table_number - b.table_number);
    }
}

registry.category("pos_available_models").add(RestaurantFloor.pythonModel, RestaurantFloor);
