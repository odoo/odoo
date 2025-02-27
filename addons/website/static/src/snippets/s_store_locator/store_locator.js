import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { StoreLocatorMapContainer } from "@website/components/store_locator_map/store_locator_map_container";

export class StoreLocator extends Interaction {
    static selector = ".s_store_locator";

    //TODO
    //Name + address in we-many2many (ask Lionel)
    //Fix map patching (will be done at the end)

    start() {
        this.createAndStartStoreLocatorApp();
    }

    createAndStartStoreLocatorApp() {
        this.el.querySelector("#store_locator_map_container")?.remove();
        const mapContainerEl = document.createElement("div");
        mapContainerEl.id = "store_locator_map_container";
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
        };
        this.mountComponent(mapContainerEl, StoreLocatorMapContainer, props);
    }
}

registry.category("public.interactions").add("website.store_locator", StoreLocator);
