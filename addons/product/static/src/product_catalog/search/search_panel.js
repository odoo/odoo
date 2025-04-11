import { SearchPanel } from "@web/search/search_panel/search_panel";
import { useState, useRef } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";


export class ProductCatalogSearchPanel extends SearchPanel {
    static template = "ProductCatalog.SearchPanel";
    static subTemplates = {
        ...SearchPanel.subTemplates,
        filtersGroup: "ProductCatalogSearchPanel.FiltersGroup",
    };

    setup() {
        super.setup();

        this.state = useState({
            ...this.state,
            sectionOfTags: {},
            sectionOfSections: new Map(),
            isAddingSection: false,
            newSectionName: "",
        });
        this.sectionInput = useRef("sectionInputRef");
        this.onDrop = this.onDrop.bind(this);
    }

    updateActiveValues() {
        super.updateActiveValues();
        this.state.sectionOfTags = this.buildSection();
        this.loadSections();
    }

    async loadSections() {
        const sections = await rpc(
            "/product/catalog/get_sections", {
            res_model: this.env.model.config.context.product_catalog_order_model,
            order_id: this.env.model.config.context.order_id,
        });

        this.state.sectionOfSections = new Map(
            sections.map(({ id, name, sequence }) => [id, { name, sequence }])
        );
        this.env.model.config.context.sections = sections;
    }

    enableSectionInput() {
        this.state.isAddingSection = true;
        setTimeout(() => this.sectionInput.el?.focus(), 100);

    }

    async createSection() {
        const sectionName = this.state.newSectionName.trim();
        if (!sectionName) return (this.state.isAddingSection = false);

        await rpc("/product/catalog/create_section", {
            res_model: this.env.model.config.context.product_catalog_order_model,
            order_id: this.env.model.config.context.order_id,
            section_name: sectionName,
        });

        this.loadSections();

        this.state.isAddingSection = false;
        this.state.newSectionName = "";
    }

    onSectionInputKeydown(event) {
        if (event.key === "Enter") {
            this.createSection();
        } else if (event.key === "Escape") {
            this.state.isAddingSection = false;
            this.state.newSectionName = "";
        }
    }

    clearSectionSelection() {
        this.env.model.config.context.selected_section = null;
        this.env.model.load();
    }

    buildSection() {
        const values = this.env.searchModel.filters[0].values;
        let sections = new Map();

        values.forEach(element => {
            const name = element.display_name;
            const id = element.id;
            const count = element.__count;
            if (sections.has(name)) {
                let currentTag = sections.get(name);
                currentTag.get('ids').push(id);
                currentTag.set('count', currentTag.get('count') + count);
            } else if (count > 0) {
                let newTag = new Map();
                newTag.set('ids', [id]);
                newTag.set('count', count);
                sections.set(name, newTag);
            }
        });

        return sections;
    }

    toggleSectionFilterValue(filterId, tagIds, { currentTarget }) {
        tagIds.forEach(id => {
            this.toggleFilterValue(filterId, id, { currentTarget });
        })
    }

    setSelectedSection(sectionId, highlightOnly) {
        const section = this.state.sectionOfSections.get(sectionId);
        if (section) {
            this.env.model.config.context.selected_section = {
                name: section.name,
                sequence: section.sequence,
                highlightOnly,
            };
        }
        this.env.model.load();
    }

    onDragStart(sectionId, ev) {
        ev.dataTransfer.setData("text/plain", sectionId);
    }

    onDragOver(ev) {
        ev.preventDefault();
    }

    onDrop(targetSecId, ev) {
        ev.preventDefault();
        const draggedSecId = ev.dataTransfer.getData("text/plain");
        if (draggedSecId !== targetSecId) this.reorderSections(draggedSecId, targetSecId);
    }

    async reorderSections(draggedSecId, targetSecId) {
        [draggedSecId, targetSecId] = [Number(draggedSecId), Number(targetSecId)];

        const draggedSection = this.state.sectionOfSections.get(draggedSecId);
        const targetSection = this.state.sectionOfSections.get(targetSecId);
        if (!draggedSection || !targetSection) return;

        [draggedSection.sequence, targetSection.sequence] =
            [targetSection.sequence, draggedSection.sequence];

        await rpc("/product/catalog/reorder_sections", {
            res_model: this.env.model.config.context.product_catalog_order_model,
            order_id: this.env.model.config.context.order_id,
            sections: [
                { id: draggedSecId, sequence: draggedSection.sequence },
                { id: targetSecId, sequence: targetSection.sequence }
            ],
        });
        this.loadSections();
    }
}
