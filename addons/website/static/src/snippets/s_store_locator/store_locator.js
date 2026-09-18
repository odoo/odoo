import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { LocationSelectorComponent } from "@website/components/location_selector/location_selector_component/location_selector_component";

export class StoreLocator extends Interaction {
    static selector = ".s_store_locator";

    setup() {
        this.dataset = this.el.dataset;
        this.props = {
            mapZoom: this.dataset.mapZoom,
            hideOffscreenLocations: this.dataset.mapHideOffscreenLocations === "true",
            locationsList: this.dataset.locationsList,
            showDetailsTextArea: this.dataset.mapDetails == "area",
            showDetailsTooltip: this.dataset.mapDetails == "tooltip",
            showEmail: this.dataset.mapShowEmail === "true",
            showImage: this.dataset.mapShowImage === "true",
            showPhone: this.dataset.mapShowPhone === "true",
            showWebsite: this.dataset.mapShowWebsite === "true",
            showSearchbar: this.dataset.mapSearchbar === "true",
            showSidebar: this.dataset.mapSidebar === "true",
            mapSearchbarPlaceholder: this.dataset.mapSearchbarPlaceholder,
            sidebarLocation: this.dataset.mapSidebarLocation,
        };
        // We need to keep track of the element's ownerDocument to correctly
        // run Leaflets in snippet previews
        this.env.windowContext = {};
        if (this.el.ownerDocument.documentElement.classList.contains("o_add_snippets_preview")) {
            this.env.windowContext = { iframePreviewDocument: this.el.ownerDocument };
        }
    }

    start() {
        const locationList = JSON.parse(this.dataset.locationsList || "[]");
        if (locationList.length) {
            this.mountComponent(
                this.el.querySelector(".o_store_locator_component"),
                LocationSelectorComponent,
                this.props
            );
        }
    }
}

registry.category("public.interactions").add("website.store_locator", StoreLocator);

registry.category("public.interactions.preview").add("website.store_locator_preview", {
    Interaction: StoreLocator,
});
