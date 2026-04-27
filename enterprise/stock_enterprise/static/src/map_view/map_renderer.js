import { MapRenderer } from "@web_map/map_view/map_renderer";

export class StockMapRenderer extends MapRenderer {
    get googleMapUrl() {
        let url = super.googleMapUrl;
        if (this.props.model.data.records.length) {
            const warehouseAddress = this.props.model.data.records[0].warehouse_address_id;
            let multiAddresses = false;
            for (const record of this.props.model.data.records) {
                if (record.warehouse_address_id.id !== warehouseAddress.id) {
                    multiAddresses = true;
                    break;
                }
            }
            if (multiAddresses) {
                return url;
            }
            url += `&origin=${warehouseAddress.contact_address_complete}`;
            url += `&destination=${warehouseAddress.contact_address_complete}`;
        }
        return url;
    }
}
