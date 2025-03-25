import { onWillStart, useState } from '@odoo/owl';
import { getActiveHotkey } from '@web/core/hotkeys/hotkey_service';
import { rpc } from '@web/core/network/rpc';
import { useBus } from '@web/core/utils/hooks';
import { SearchPanel } from '@web/search/search_panel/search_panel';


export class ProductCatalogSearchPanel extends SearchPanel {
    static template = 'product.SearchPanel';

    setup() {
        super.setup();

        this.state = useState({
            ...this.state,
            sectionOfSections: new Map(),
            isAddingSection: '',
            newSectionName: "",
        });

        useBus(this.env.searchModel, 'section-line-count-change', this.updateSectionLineCount);

        onWillStart(async () =>  await this.loadSections());
    }

    get showSections() {
        return this.env.model.config.context.product_catalog_order_id;
    }

    get selectedSection() {
        return this.env.searchModel.selectedSection;
    }

    onDragStart(sectionId, ev) {
        ev.dataTransfer.setData('section_id', sectionId);
    }

    onDragOver(ev) {
        ev.preventDefault();
    }

    onDrop(targetSecId, ev) {
        ev.preventDefault();
        const moveSecId = ev.dataTransfer.getData('section_id');
        if (moveSecId !== targetSecId) this.reorderSections(moveSecId, targetSecId);
    }

    enableSectionInput(isAddingSection) {
        this.state.isAddingSection = isAddingSection;
        setTimeout(() => document.querySelector('.o_section_input')?.focus(), 100);
    }

    onSectionInputKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        if (hotkey === 'enter') {
            this.createSection();
        } else if (hotkey === 'escape') {
            Object.assign(this.state, {
                isAddingSection: '',
                newSectionName: "",
            });
        }
    }

    setSelectedSection(sectionId=null, filtered=false) {
        this.env.searchModel.setSelectedSection(sectionId, filtered);
    }

    async createSection() {
        const sectionName = this.state.newSectionName.trim();
        if (!sectionName) return this.state.isAddingSection = '';

        const sections = this.state.sectionOfSections;

        const extraParams = {
            name: sectionName,
            position: this.state.isAddingSection,
        };
        let newLineCount = 0;

        const section = await rpc('/product/catalog/create_section',
            this._getSectionInfoParams(extraParams)
        );

        if (section) {
            if (extraParams.position === 'top') {
                newLineCount = sections.get(false).line_count;
                sections.delete(false);
            }
            sections.set(section.id, {
                name: this.state.newSectionName,
                sequence: section.sequence,
                line_count: newLineCount,
            });
            this._sortSectionsBySequence(sections);
            this.setSelectedSection(section.id);
        }
        Object.assign(this.state, {
            isAddingSection: '',
            newSectionName: "",
        });
    }

    async loadSections() {
        if (!this.showSections) return;
        const sections = await rpc('/product/catalog/get_sections', this._getSectionInfoParams());

        const sectionMap = new Map();
        for (const {id, name, sequence, line_count} of sections) {
            sectionMap.set(id, {name, sequence, line_count});
        }
        this.state.sectionOfSections = sectionMap;
        this.setSelectedSection(sectionMap.size > 0 ? [...sectionMap.keys()][0] : null);
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
            section && (section.sequence = sequence);
        }
        const noSection = sections.get(false);
        noSection && (noSection.sequence = 0); // Reset the sequence of the "No Section"
        this._sortSectionsBySequence(sections);
    }

    updateSectionLineCount({detail: {sectionId, lineCountChange}}) {
        const sections = this.state.sectionOfSections;
        const section = sections.get(sectionId);
        if (!section) return;

        section.line_count = Math.max(0, section.line_count + lineCountChange);

        if (section.line_count === 0 && sectionId === false && sections.size > 1) {
            sections.delete(sectionId);
            this.setSelectedSection(sections.size > 0 ? [...sections.keys()][0] : null);
        }
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

    _sortSectionsBySequence(sections) {
        this.state.sectionOfSections = new Map(
            [...sections].sort((a, b) => a[1].sequence - b[1].sequence)
        );
    }
}
