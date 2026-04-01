import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { LocationSelectorComponent } from "@website/components/location_selector/location_selector_component/location_selector_component";

export class StoreLocator extends Interaction {
    static selector = ".s_store_locator";

    start() {
        const dataset = this.el.dataset;
        const props = {
            mapZoom: dataset.mapZoom,
            hideOffscreenLocations: dataset.mapHideOffscreenLocations === "true" ? true : false,
            locationsList: dataset.locationsList,
            showDetailsTextArea: dataset.mapDetails == "area",
            showDetailsTooltip: dataset.mapDetails == "tooltip",
            showEmail: dataset.mapShowEmail === "true" ? true : false,
            showImage: dataset.mapShowImage === "true" ? true : false,
            showPhone: dataset.mapShowPhone === "true" ? true : false,
            showWebsite: dataset.mapShowWebsite === "true" ? true : false,
            showSearchbar: dataset.mapSearchbar === "true" ? true : false,
            showSidebar: dataset.mapSidebar === "true" ? true : false,
            mapSearchbarPlaceholder: dataset.mapSearchbarPlaceholder,
            sidebarLocation: dataset.mapSidebarLocation,
            containerEl: this.el,
        };
        this.mountComponent(
            this.el.querySelector(".o_store_locator_component"),
            LocationSelectorComponent,
            props
        );
    }
}

registry.category("public.interactions").add("website.store_locator", StoreLocator);

registry.category("public.interactions.preview").add("website.store_locator_preview", {
    Interaction: StoreLocator,
});
