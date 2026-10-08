import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { onWillStart, proxy, usePlugin } from "@odoo/owl";
import { ORM } from "@web/core/orm_plugin";
import { registry } from "@web/core/registry";
import { useDomState } from "@html_builder/core/utils";

const STORE_LOCATOR_PARTNER_DOMAIN = [
    ["city", "!=", false],
    ["street", "!=", false],
    ["zip", "!=", false],
];
const STORE_LOCATOR_SEARCH_LIMIT = 50;
export const STORE_LOCATOR_PARTNER_FIELDS = [
    "city",
    "contact_address_inline",
    "country_id",
    "country_code",
    "display_name",
    "email",
    "image_256",
    "name",
    "partner_latitude",
    "partner_longitude",
    "phone",
    "street",
    "zip",
    "website",
];

export class StoreLocatorOption extends BaseOptionComponent {
    static template = "website.StoreLocatorOption";
    static id = "store_locator_option";

    mapZoomOptions = [
        { value: "19", label: "10 m" },
        { value: "18", label: "20 m" },
        { value: "17", label: "50 m" },
        { value: "16", label: "100 m" },
        { value: "15", label: "200 m" },
        { value: "14", label: "400 m" },
        { value: "13", label: "1 km" },
        { value: "12", label: "2 km" },
        { value: "11", label: "4 km" },
        { value: "10", label: "8 km" },
        { value: "9", label: "15 km" },
        { value: "8", label: "30 km" },
        { value: "7", label: "50 km" },
        { value: "6", label: "100 km" },
        { value: "5", label: "200 km" },
        { value: "4", label: "400 km" },
        { value: "3", label: "1000 km" },
        { value: "2", label: "2000 km" },
    ];

    setup() {
        super.setup();
        this.orm = usePlugin(ORM);
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
