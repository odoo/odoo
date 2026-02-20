import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { LocationSelectorComponent } from "@website/components/location_selector/location_selector_component/location_selector_component";

export class StoreLocator extends Interaction {
    static selector = ".s_store_locator";

    start() {
        const dataset = this.el.dataset;
        const props = {
            mapZoom: dataset.mapZoom,
            hideOffscreenLocations: dataset.mapHideOffscreenLocations,
            locationsList: dataset.locationsList,
            showDetailsTextArea: dataset.mapDetails == "area",
            showDetailsTooltip: dataset.mapDetails == "tooltip",
            showEmail: dataset.mapShowEmail,
            showImage: dataset.mapShowImage,
            showPhone: dataset.mapShowPhone,
            showWebsite: dataset.mapShowWebsite,
            showSearchbar: dataset.mapSearchbar,
            showSidebar: dataset.mapSidebar,
            sidebarLocation: dataset.mapSidebarLocation,
        };
        this.mountComponent(
            this.el.querySelector(".o_store_locator_component"),
            LocationSelectorComponent,
            props
        );
    }
}

registry.category("public.interactions").add("website.store_locator", StoreLocator);
