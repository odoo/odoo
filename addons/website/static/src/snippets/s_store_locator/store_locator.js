import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { LocationSelectorComponent } from "@website/components/location_selector/location_selector_component/location_selector_component";

export class StoreLocator extends Interaction {
    static selector = ".s_store_locator";

    start() {
        const dataset = this.el.dataset;
        const props = {
            mapZoom: dataset.mapZoom,
            hideOffscreenLocations: dataset.mapHideOffscreenLocations === "true",
            locationsList: dataset.locationsList,
            showDetailsTextArea: dataset.mapDetails == "area",
            showDetailsTooltip: dataset.mapDetails == "tooltip",
            showEmail: dataset.mapShowEmail === "true",
            showImage: dataset.mapShowImage === "true",
            showPhone: dataset.mapShowPhone === "true",
            showWebsite: dataset.mapShowWebsite === "true",
            showSearchbar: dataset.mapSearchbar === "true",
            showSidebar: dataset.mapSidebar === "true",
            mapSearchbarPlaceholder: dataset.mapSearchbarPlaceholder,
            sidebarLocation: dataset.mapSidebarLocation,
        };

        // We need to keep track of the element's ownerDocument to correctly
        // run Leaflets in snippet previews
        this.env.windowContext = {};
        if (this.el.ownerDocument.documentElement.classList.contains("o_add_snippets_preview")) {
            this.env.windowContext = { iframePreviewDocument: this.el.ownerDocument };
        }

        const locationList = JSON.parse(dataset.locationsList || "[]");
        if (locationList.length) {
            this.mountComponent(
                this.el.querySelector(".o_store_locator_component"),
                LocationSelectorComponent,
                props
            );
        }
    }
}

registry.category("public.interactions").add("website.store_locator", StoreLocator);

registry.category("public.interactions.preview").add("website.store_locator_preview", {
    Interaction: StoreLocator,
});
