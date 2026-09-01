import { SearchModel } from "@web/search/search_model";

export class AccountProductCatalogSearchModel extends SearchModel {
    setup() {
        super.setup(...arguments);
        this.selectedSectionId = null;
        this.filterBySection = false;
        this.catalogSections = [];
        this.catalogOrderDetails = { name: "", amount_untaxed: 0.0 };
    }

    async load(config) {
        await super.load(config);

        const showSections = config.context.show_sections;
        if (!showSections) {
            return;
        }

        const { order_details, sections } = await this.orm.call(
            config.context.product_catalog_order_model,
            "get_catalog_section_data",
            [config.context.product_catalog_order_id],
            { child_field: config.context.child_field }
        );
        this.catalogOrderDetails = order_details;
        this.catalogSections = sections;

        if (sections.length) {
            this.selectedSectionId = sections[sections.length - 1].id;
        }
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
