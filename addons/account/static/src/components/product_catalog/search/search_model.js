import { SearchModel } from "@web/search/search_model";

export class AccountProductCatalogSearchModel extends SearchModel {
    setup() {
        super.setup(...arguments);
        this.selectedSectionId = null;
        this.filterBySection = false;
    }

    setSelectedSection(sectionId) {
        this.selectedSectionId = sectionId;
        this._notify();
    }

    setFilterBySection(filtered) {
        this.filterBySection = filtered;
        this._notify();
    }
}
