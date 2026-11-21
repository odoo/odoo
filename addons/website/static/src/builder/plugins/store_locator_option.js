import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { onWillStart, proxy, usePlugin } from "@odoo/owl";
import { ORM } from "@web/core/orm_plugin";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useDomState } from "@html_builder/core/utils";
import { OSM_MAX_ZOOM } from "@website/components/location_selector/map/map";
import { getMapZoomLevels } from "./map_zoom_utils";

const STORE_LOCATOR_PARTNER_DOMAIN = [
    ["city", "!=", false],
    ["street", "!=", false],
    ["zip", "!=", false],
];
const STORE_LOCATOR_SEARCH_LIMIT = 50;
// The page source always contains these partner fields.
// There are optional fields too: see `STORE_LOCATOR_OPTIONAL_FIELDS`.
export const STORE_LOCATOR_PARTNER_FIELDS = [
    "city",
    "contact_address_inline",
    "country_id",
    "country_code",
    "display_name",
    "name",
    "partner_latitude",
    "partner_longitude",
    "street",
    "zip",
];

export class StoreLocatorOption extends BaseOptionComponent {
    static template = "website.StoreLocatorOption";
    static id = "store_locator_option";

    setup() {
        super.setup();
        this.orm = usePlugin(ORM);
        this.mapZoomLevels = getMapZoomLevels(
            useService("website").currentWebsite.distance_unit,
            OSM_MAX_ZOOM
        );
        this.editingElement = this.env.getEditingElement();
        this.hasAvailableRecords = false;
        this.listState = proxy({
            availableRecords: "[]",
        });
        this.state = useDomState((editingElement) => ({
            hasLocations: JSON.parse(editingElement.dataset.locationsList || "[]").length > 0,
        }));

        onWillStart(async () => {
            const searchResult = await this.searchAvailableRecords("");
            this.listState.availableRecords = JSON.stringify(searchResult ?? []);
            this.hasAvailableRecords = searchResult?.length > 0;
        });
    }

    async searchAvailableRecords(searchString, excludeIds) {
        let domain = searchString
            ? [...STORE_LOCATOR_PARTNER_DOMAIN, ["display_name", "ilike", searchString]]
            : STORE_LOCATOR_PARTNER_DOMAIN;
        if (excludeIds?.length) {
            domain = [...domain, ["id", "not in", excludeIds]];
        }
        const searchResult = await this.orm.searchRead(
            "res.partner",
            domain,
            STORE_LOCATOR_PARTNER_FIELDS,
            { limit: STORE_LOCATOR_SEARCH_LIMIT }
        );
        return searchResult;
    }

    async onInput(searchString) {
        const searchTime = Date.now();
        this.lastSearchTime = searchTime;
        const locationsList = JSON.parse(this.editingElement.dataset.locationsList || "[]");
        const excludeIds = locationsList.map((location) => location.id);
        const searchResult = await this.searchAvailableRecords(searchString, excludeIds);
        if (searchTime < this.lastSearchTime) {
            return;
        }
        if (searchResult.length > 0) {
            this.listState.availableRecords = JSON.stringify(searchResult);
        }
    }
}

registry.category("builder-options").add(StoreLocatorOption.id, StoreLocatorOption);
