import { MapModel } from "@web_map/map_view/map_model";

export class StockMapModel extends MapModel {
    _getRecordSpecification(metaData, data) {
        return {
            ...super._getRecordSpecification(metaData, data),
            warehouse_address_id: {
                fields: {
                    display_name: {},
                    contact_address_complete: {},
                }
            }
        }
    }
}