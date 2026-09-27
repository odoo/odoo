import { SearchPanel } from "@web/search/search_panel/search_panel";

export class ProductCatalogSearchPanel extends SearchPanel {
    static template = "product.ProductCatalogSearchPanel";

    setup() {
        super.setup();
        this.state.mobileDrawerOpen = false;
    }

    openMobileDrawer() {
        this.state.mobileDrawerOpen = true;
    }

    closeMobileDrawer() {
        this.state.mobileDrawerOpen = false;
    }

    clearSelection(sectionId = 0) {
        super.clearSelection(sectionId);
        this.closeMobileDrawer();
    }

    async toggleCategory(category, value) {
        await super.toggleCategory(category, value);
        if (this.uiService.isSmall && !value.childrenIds.length) {
            this.closeMobileDrawer();
        }
    }
}
