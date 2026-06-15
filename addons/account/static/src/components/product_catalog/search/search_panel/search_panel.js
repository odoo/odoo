import { onPatched, onWillStart, proxy } from "@odoo/owl";
import { formatCurrency } from "@web/core/currency";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { useBus, useService } from "@web/core/utils/hooks";
import { useNestedSortable } from "@web/core/utils/nested_sortable";
import { useRef, useSubEnv } from "@web/owl2/utils";
import { SearchPanel } from "@web/search/search_panel/search_panel";
import { SectionRow } from "../section_row/section_row";

export class AccountProductCatalogSearchPanel extends SearchPanel {
    static template = "account.ProductCatalogSearchPanel";
    static components = { ...SearchPanel.components, SectionRow };

    setup() {
        super.setup();

        this.orm = useService("orm");

        this.state = proxy({
            ...this.state,
            dragging: false,
            addingSectionTarget: "",
            newSectionName: "",
            renamingSectionId: null,
            sections: [],
            totalUntaxedAmount: 0.0,
        });

        useSubEnv({
            setSelectedSection: this.setSelectedSection.bind(this),
            enableSectionInput: this.enableSectionInput.bind(this),
            enableRenameSectionInput: this.enableRenameSectionInput.bind(this),
            getFormattedSubTotal: this.getFormattedSubTotal.bind(this),
            createSection: this.createSection.bind(this),
            renameSection: this.renameSection.bind(this),
            onSectionInputKeydown: this.onSectionInputKeydown.bind(this),
            duplicateSection: this.duplicateSection.bind(this),
            deleteSection: this.deleteSection.bind(this),
        });

        useBus(this.env.searchModel, "section-subtotal-change", this.updateSectionSubtotal);

        onWillStart(async () => {
            if (!this.showSections) {
                return;
            }

            const { order_details, sections } = await this.orm.call(
                this.env.model.config.context.product_catalog_order_model,
                "get_catalog_data",
                [this.env.model.config.context.order_id],
                {
                    child_field: this.env.model.config.context.child_field,
                }
            );

            this.order = {
                name: order_details.name,
                currency_id: order_details.currency_id,
            };
            this.state.totalUntaxedAmount = order_details.amount_untaxed;

            this._setSectionsState(sections);
            if (this.state.sections.length) {
                this.setSelectedSection(this.state.sections[0].id);
            }
        });

        this.sectionTreeRef = useRef("sectionTreeRef");
        this.sectionInputRef = useRef("sectionInputRef");

        onPatched(() => {
            if (this.state.addingSectionTarget) {
                this.sectionInputRef.el?.focus();
            }
        });

        useNestedSortable({
            ref: this.sectionTreeRef,
            nest: true,
            useElementSize: true,
            maxLevels: 2,
            isAllowed: ({ element, placeHolder }) => {
                const id = parseInt(element.dataset.id);
                const node = id && this._findSectionById(id);
                if (!node) {
                    return false;
                }

                const targetParentId =
                    placeHolder.parentElement?.closest("li.o_section")?.dataset.id || false;

                // allow only if both are same level (section <-> section OR
                // subsection <-> subsection)
                return Boolean(node.parent_id) === Boolean(targetParentId);
            },

            onDragStart: () => {
                this.state.dragging = true;
            },

            onDragEnd: () => {
                this.state.dragging = false;
            },

            onDrop: (params) => this.resequenceSections(params),
        });
    }

    updateActiveValues() {
        super.updateActiveValues();
        this.state.sidebarExpanded ||= this.showSections;
    }

    get showSections() {
        return this.env.model.config.context.show_sections;
    }

    get selectedSection() {
        return this.env.searchModel.selectedSection;
    }

    enableSectionInput(parentId = null) {
        this.state.addingSectionTarget = parentId ? `subsection_${parentId}` : "section";
    }

    enableRenameSectionInput(section) {
        this.state.renamingSectionId = section.id;
        this.state.newSectionName = section.name;
    }

    getFormattedSubTotal(amount) {
        return formatCurrency(amount, this.order.currency_id);
    }

    onSectionInputKeydown(ev, parentId, renameId = null) {
        if (this.env.isSmall) {
            return;
        }

        const hotkey = getActiveHotkey(ev);
        if (hotkey === "enter") {
            if (renameId) {
                this.renameSection(renameId);
            } else {
                this.createSection(parentId);
            }
        } else if (hotkey === "escape") {
            Object.assign(this.state, {
                addingSectionTarget: "",
                newSectionName: "",
                renamingSectionId: null,
            });
        }
    }

    setSelectedSection(sectionId = null, filtered = false) {
        this.env.searchModel.setSelectedSection(sectionId, filtered);
        if (sectionId) {
            const section = this._findSectionById(sectionId);
            if (section.children.length) {
                section.isOpen = !section.isOpen;
            }
        }
    }

    async createSection(parentId = null) {
        const sectionName = this.state.newSectionName.trim();
        if (!sectionName) {
            this.state.addingSectionTarget = "";
            return;
        }

        const section = await this.orm.call(
            this.env.model.config.context.product_catalog_order_model,
            "create_section",
            [this.env.model.config.context.order_id],
            {
                child_field: this.env.model.config.context.child_field,
                name: sectionName,
                parent_id: parentId,
            }
        );

        if (section) {
            const newNode = {
                ...section,
                name: sectionName,
                children: [],
                isOpen: true,
                parent_id: parentId,
            };

            if (parentId) {
                const parent = this._findSectionById(parentId);
                parent.children.push(newNode);
                parent.isOpen = true;
            } else {
                this.state.sections.push(newNode);
            }
            this.setSelectedSection(section.id);
        }
        Object.assign(this.state, {
            addingSectionTarget: "",
            newSectionName: "",
        });
    }

    async deleteSection(section) {
        await this.orm.call(
            this.env.model.config.context.product_catalog_order_model,
            "delete_section",
            [this.env.model.config.context.order_id],
            {
                child_field: this.env.model.config.context.child_field,
                section_id: section.id,
            }
        );

        if (section.parent_id) {
            const parent = this._findSectionById(section.parent_id);
            parent.children = parent.children.filter((c) => c.id !== section.id);
        } else {
            this.state.sections = this.state.sections.filter((s) => s.id !== section.id);
        }

        this.env.searchModel.trigger("section-subtotal-change", {
            sectionId: section.parent_id || section.id,
            subtotalDelta: -section.subtotal,
        });

        const { sectionId, filtered } = this.selectedSection;

        if (sectionId === section.id) {
            this.setSelectedSection(this.state.sections[0]?.id || false, false);
        } else if (sectionId === section.parent_id) {
            this.setSelectedSection(sectionId, filtered);
        }
    }

    async duplicateSection(section) {
        const { sections, duplicated_section_id } = await this.orm.call(
            this.env.model.config.context.product_catalog_order_model,
            "duplicate_section",
            [this.env.model.config.context.order_id],
            {
                child_field: this.env.model.config.context.child_field,
                section_id: section.id,
                parent_id: section.parent_id,
            }
        );

        this._setSectionsState(sections);
        this.env.setSelectedSection(duplicated_section_id, false);
    }

    async renameSection(sectionId) {
        const name = this.state.newSectionName.trim();
        if (!name) {
            this.state.renamingSectionId = null;
            return;
        }

        await this.orm.call(
            this.env.model.config.context.product_catalog_order_model,
            "rename_section",
            [this.env.model.config.context.order_id],
            {
                child_field: this.env.model.config.context.child_field,
                section_id: sectionId,
                new_name: name,
            }
        );

        const section = this._findSectionById(sectionId);
        if (section) {
            section.name = name;
        }

        this.state.renamingSectionId = null;
        this.state.newSectionName = "";
    }

    async resequenceSections({ element, parent, next }) {
        const movedSectionId = parseInt(element.dataset.id);
        if (!movedSectionId) {
            return;
        }

        const newParentSectionId = parent ? parseInt(parent.dataset.id) : false;
        const insertBeforeSectionSequence = next ? parseInt(next.dataset.sequence) : null;
        const insertBeforeSectionId = next ? parseInt(next.dataset.id) : null;

        const node = this._extractNode(movedSectionId);
        if (!node) {
            return;
        }

        node.parent_id = newParentSectionId;

        const parentNode = newParentSectionId ? this._findSectionById(newParentSectionId) : null;
        const list = parentNode ? parentNode.children : this.state.sections;

        const index = insertBeforeSectionId
            ? list.findIndex((n) => n.id === insertBeforeSectionId)
            : list.length;

        list.splice(index >= 0 ? index : list.length, 0, node);

        if (parentNode) {
            parentNode.isOpen = true;
        }

        await this.orm.call(
            this.env.model.config.context.product_catalog_order_model,
            "resequence_sections",
            [this.env.model.config.context.order_id],
            {
                child_field: this.env.model.config.context.child_field,
                moved_section_id: movedSectionId,
                new_parent_section_id: newParentSectionId,
                insert_before_section_sequence: insertBeforeSectionSequence,
            }
        );
    }

    updateSectionSubtotal({ detail: { sectionId, subtotalDelta } }) {
        this.state.totalUntaxedAmount += subtotalDelta;

        const section = this._findSectionById(sectionId);
        if (!section) {
            return;
        }

        section.subtotal += subtotalDelta;

        if (section.parent_id) {
            const parent = this._findSectionById(section.parent_id);
            if (parent) {
                parent.subtotal += subtotalDelta;
            }
        }
    }

    _setSectionsState(sections) {
        const sectionsById = new Map();
        const rootSections = [];

        for (const section of sections) {
            const node = {
                ...section,
                children: [],
                isOpen: false,
            };

            sectionsById.set(section.id, node);

            if (section.parent_id) {
                sectionsById.get(section.parent_id)?.children.push(node);
            } else {
                rootSections.push(node);
            }
        }

        this.state.sections = rootSections;
    }

    _findSectionById(id) {
        for (const sec of this.state.sections) {
            if (sec.id === id) {
                return sec;
            }

            const child = sec.children.find((c) => c.id === id);
            if (child) {
                return child;
            }
        }
        return null;
    }

    _extractNode(id) {
        const rootIdx = this.state.sections.findIndex((n) => n.id === id);
        if (rootIdx !== -1) {
            return this.state.sections.splice(rootIdx, 1)[0];
        }
        for (const section of this.state.sections) {
            const idx = section.children.findIndex((n) => n.id === id);
            if (idx !== -1) {
                return section.children.splice(idx, 1)[0];
            }
        }
        return null;
    }
}
