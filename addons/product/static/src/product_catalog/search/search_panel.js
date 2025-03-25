import { onWillStart, useState } from "@odoo/owl";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { rpc } from "@web/core/network/rpc";
import { useBus } from "@web/core/utils/hooks";
import { SearchPanel } from "@web/search/search_panel/search_panel";


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
        this.onDrop = this.onDrop.bind(this);

        useBus(this.env.searchModel, "section-line-count-change", this.updateSectionLineCount);

        onWillStart(async () =>  await this.loadSections());
    }

    get showSections() {
        return this.env.model.config.context.product_catalog_order_id;
    }

    get selectedSection() {
        return this.env.searchModel.selectedSection;
    }

    updateActiveValues() {
        super.updateActiveValues();
        this.state.sectionOfTags = this.buildSectionOfTags();
    }

    buildSectionOfTags() {
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

    toggleTagFilterValue(filterId, tagIds, { currentTarget }) {
        tagIds.forEach(id => {
            this.toggleFilterValue(filterId, id, { currentTarget });
        })
    }

    onDragStart(sectionId, ev) {
        ev.dataTransfer.setData('text/plain', sectionId);
    }

    onDragOver(ev) {
        ev.preventDefault();
    }

    onDrop(targetSecId, ev) {
        ev.preventDefault();
        const moveSecId = ev.dataTransfer.getData('text/plain');
        if (moveSecId !== targetSecId) this.reorderSections(moveSecId, targetSecId);
    }

    enableSectionInput() {
        this.state.isAddingSection = true;
        setTimeout(() => document.querySelector('.o_section_input')?.focus(), 100);
    }

    onSectionInputKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        if (hotkey === 'enter') {
            this.createSection();
        } else if (hotkey === 'escape') {
            Object.assign(this.state, {
                isAddingSection: false,
                newSectionName: "",
            });
        }
    }

    setSelectedSection(sectionId=false, filtered=false) {
        this.env.searchModel.setSelectedSection(sectionId, filtered);
    }

    async createSection() {
        const sectionName = this.state.newSectionName.trim();
        if (!sectionName) return this.state.isAddingSection = false;

        const section = await rpc('/product/catalog/create_section',
            this._getSectionInfoParams({section_name: sectionName})
        );

        if (section) {
            this.state.sectionOfSections.set(section.id, {
                name: section.name,
                sequence: section.sequence,
                line_count: 0,
            });
            this.setSelectedSection(section.id);
        }
        Object.assign(this.state, {
            isAddingSection: false,
            newSectionName: "",
        });
    }

    async loadSections() {
        if (!this.showSections) return;
        const sections = await rpc('/product/catalog/get_sections', this._getSectionInfoParams());

        const sectionMap = this.state.sectionOfSections || new Map();
        for (const {id, name, sequence, line_count} of sections) {
            if (!sectionMap.get(id)) {
                sectionMap.set(id, {name, sequence, line_count});
            }
        }
        this.state.sectionOfSections = sectionMap;
    }

    async reorderSections(moveId, targetId) {
        [moveId, targetId] = [parseInt(moveId), parseInt(targetId)];
        const sections = this.state.sectionOfSections;
        const moveSection = sections.get(moveId);
        const targetSection = sections.get(targetId);

        if (!moveSection || !targetSection) return;

        const updatedSequences = await rpc('/product/catalog/resequence_sections',
            this._getSectionInfoParams({
                sections: [
                    { id: moveId, sequence: moveSection.sequence },
                    { id: targetId, sequence: targetSection.sequence },
                ],
            })
        );
        for (const [id, sequence] of Object.entries(updatedSequences)) {
            const section = sections.get(parseInt(id));
            if (section) {
                section.sequence = sequence;
            }
        }
        this.state.sectionOfSections = new Map(
            [...sections].sort((a, b) => a[1].sequence - b[1].sequence)
        );
    }

    _getSectionInfoParams(extra = {}) {
        const ctx = this.env.model.config.context;
        return {
            res_model: ctx.product_catalog_order_model,
            order_id: ctx.order_id,
            child_field: ctx.child_field,
            ...extra,
        };
    }

    updateSectionLineCount({detail: {sectionId, lineCountChange}}) {
        const section = this.state.sectionOfSections.get(sectionId);
        if (section) {
            section.line_count = Math.max(0, section.line_count + lineCountChange);
        }
    }
}
