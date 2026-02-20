import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { useService } from "@web/core/utils/hooks";
import { onWillStart } from "@odoo/owl";

export const STORE_LOCATOR_PARTNER_FIELDS = [
    "city",
    "name",
    "contact_address_inline",
    "country_id",
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
    static selector = ".s_store_locator";

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
        this.orm = useService("orm");
        this.state = useDomState((editingElement) => {
            const locations = JSON.parse(editingElement.dataset.locationsList || "[]");
            return {
                hasLocations: !!locations.length,
                availableRecords: this.state.availableRecords ?? "[]",
            };
        });

        onWillStart(async () => {
            const searchResult = await this.orm.searchRead(
                "res.partner",
                [
                    ["is_company", "=", true],
                    ["city", "!=", false],
                    ["street", "!=", false],
                    ["zip", "!=", false],
                ],
                STORE_LOCATOR_PARTNER_FIELDS
            );
            this.state.availableRecords = JSON.stringify(searchResult);
        });
    }
}
