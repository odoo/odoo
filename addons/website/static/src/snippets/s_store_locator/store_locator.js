import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { StoreLocatorComponent } from "@website/components/store_locator_map/store_locator_component";

export class StoreLocator extends Interaction {
    static selector = ".s_store_locator";

    start() {
        this.createAndStartStoreLocatorApp();
    }

    createAndStartStoreLocatorApp() {
        this.el.querySelector("#store_locator_component")?.remove();
        const mapContainerEl = document.createElement("div");
        mapContainerEl.id = "store_locator_component";
        mapContainerEl.classList.add("border-0");
        mapContainerEl.classList.add("h-100");
        this.el.appendChild(mapContainerEl);
        const dataset = this.el.dataset;
        const props = {
            rootEl: this.el,
            type: dataset.mapType,
            zoom: dataset.mapZoom,
            searchbar: dataset.mapSearchbar == "true",
            sidebar: dataset.mapSidebar == "true",
            sidebarLocation: dataset.mapSidebarLocation,
            details: dataset.mapDetails,
            offscreenLocationsHidden: dataset.offscreenLocationsHidden == "true",
        };
        this.mountComponent(mapContainerEl, StoreLocatorComponent, props);
    }
}

registry.category("public.interactions").add("website.store_locator", StoreLocator);
