import { SearchModel } from "@web/search/search_model";

export class AccountProductCatalogSearchModel extends SearchModel {
    setup() {
        super.setup(...arguments);
        this.selectedSection = {sectionId: null, filtered: false};
    }

    setSelectedSection(sectionId, filtered) {
        this.selectedSection = {sectionId, filtered};
        this._notify();
    }
}
