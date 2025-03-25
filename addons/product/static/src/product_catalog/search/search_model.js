import { SearchModel } from "@web/search/search_model";

export class ProductCatalogSearchModel extends SearchModel {
    setup() {
        super.setup(...arguments);
        this.selectedSection = {sectionId: null, filtered: false};
    }

    setSelectedSection(sectionId, filtered) {
        this.selectedSection = {sectionId, filtered};
        this._notify();
    }
}
