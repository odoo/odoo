import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";

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
        this.state = useDomState((editingElement) => {
            const locations = JSON.parse(editingElement.dataset.locationsList || "[]");
            return {
                hasLocations: !!locations.length,
            };
        });
    }
}
