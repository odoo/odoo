import { proxy, signal } from "@odoo/owl";
import { formatCurrency } from "@web/core/currency";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_utils";
import { useBus, useService } from "@web/core/utils/hooks";
import { useNestedSortable } from "@web/core/utils/nested_sortable";
import { useSubEnv } from "@web/owl2/utils";
import { ProductCatalogSearchPanel } from "@product/product_catalog/product_catalog_search_panel";
import { SectionRow } from "../section_row/section_row";

export class AccountProductCatalogSearchPanel extends ProductCatalogSearchPanel {
    static template = "account.ProductCatalogSearchPanel";
    static components = { ...ProductCatalogSearchPanel.components, SectionRow };

    sectionTreeRef = signal.ref();

    setup() {
        super.setup();

        this.showSections = this.env.model.config.context.show_sections;
        if (!this.showSections) {
            return;
        }

        this.orderModel = this.env.model.config.context.product_catalog_order_model;
        this.childField = this.env.model.config.context.child_field;
        this.orderId = this.env.model.config.context.order_id;
        this.currencyId = this.env.model.config.context.product_catalog_currency_id;

        this.orm = useService("orm");

        this.state = proxy({
            ...this.state,
            editingSectionId: undefined,
            sections: [],
            totalUntaxedAmount: 0.0,
        });

        useSubEnv({
            formatAmount: this.formatAmount.bind(this),
            setSelectedSection: this.setSelectedSection.bind(this),
            toggleSection: this.toggleSection.bind(this),
            toggleSectionFilter: this.toggleSectionFilter.bind(this),
            enableSectionInput: this.enableSectionInput.bind(this),
            enableRenameSectionInput: this.enableRenameSectionInput.bind(this),
            renameSection: this.renameSection.bind(this),
            onSectionInputKeydown: this.onSectionInputKeydown.bind(this),
            duplicateSection: this.duplicateSection.bind(this),
            deleteSection: this.deleteSection.bind(this),
        });

        useBus(this.env.searchModel, "section-subtotal-change", ({ detail }) => {
            this.updateSectionSubtotal(detail.sectionId, detail.subtotalDelta);
        });

        this.orderName = this.env.searchModel.catalogOrderDetails.name;
        this.state.totalUntaxedAmount = this.env.searchModel.catalogOrderDetails.amount_untaxed;
        this._setSectionsState(this.env.searchModel.catalogSections);

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

            preventDrag: () => this.editingSection,

            onDrop: (params) => this.resequenceSections(params),
        });
    }

    updateActiveValues() {
        super.updateActiveValues();
        this.state.sidebarExpanded ||= this.showSections;
    }

    get selectedSectionId() {
        return this.env.searchModel.selectedSectionId;
    }

    get filterBySection() {
        return this.env.searchModel.filterBySection;
    }

    get editingSection() {
        return this.editingSectionId !== undefined;
    }

    formatAmount(amount) {
        return formatCurrency(amount, this.currencyId);
    }

    setSelectedSection(sectionId) {
        if (!sectionId && this.state.editingSectionId === sectionId) {
            // clicks on an unsaved section should not trigger anything
            return
        }

        if (this.selectedSectionId === sectionId) {
            // if already the selected section, (un)collapse the child sections
            this.toggleSection(sectionId);
            return;
        }

        this.env.searchModel.setSelectedSection(sectionId);
    }

    enableSectionInput(parentId = null) {
        if (this.editingSection) {
            // forbid editing another line when one is still being edited
            return;
        }

        const newSection = {
            name: "",
            id: false,
            children: [],
            editing: true,
        };
        if (parentId) {
            const parentSection = this._findSectionById(parentId);
            parentSection.children.push({
                ...newSection,
                parent_id: parentId,
            });
            parentSection.isOpen = true;
        } else {
            this.state.sections.push(newSection);
        }
        this.state.editingSectionId = false;
    }

    enableRenameSectionInput(sectionId) {
        this.state.editingSectionId = sectionId;
        this._findSectionById(sectionId).editing = true;
        this.setSelectedSection(sectionId);
    }

    onSectionInputKeydown(ev, sectionId) {
        if (this.env.isSmall) {
            return;
        }

        const hotkey = getActiveHotkey(ev);
        if (hotkey === "enter") {
            this.renameSection(sectionId, ev.target.value);
        } else if (hotkey === "escape") {
            this.leaveEditionMode(sectionId);
        }
    }

    leaveEditionMode(sectionId) {
        if (!sectionId) {
            const newSection = this._findSectionById(sectionId);
            if (newSection.parent_id) {
                const parentSection = this._findSectionById(newSection.parent_id);
                parentSection.children = parentSection.children.filter(
                    (subSection) => subSection.id !== false
                );
            }
            this.state.sections = this.state.sections.filter((section) => section.id !== false);

            // focus back on the parent/first section since the (sub)section creation was cancelled
            this.setSelectedSection(newSection.parent_id || this.state.sections[0]?.id);
        } else {
            this._findSectionById(this.state.editingSectionId).editing = false;
        }
        this.state.editingSectionId = undefined;
    }

    toggleSection(sectionId) {
        // No need to call _findSectionById, only parent sections can be (un)folded.
        const section = this.state.sections.find((section) => section.id === sectionId);
        if (section?.children.length) {
            section.isOpen = !section.isOpen;
        }
    }

    toggleSectionFilter() {
        this.env.searchModel.setFilterBySection(!this.filterBySection);
    }

    async deleteSection(sectionId) {
        const section = this._findSectionById(sectionId);
        await this.orm.call(this.orderModel, "delete_section", [this.orderId], {
            child_field: this.childField,
            section_id: sectionId,
        });

        if (section.parent_id) {
            const parent = this._findSectionById(section.parent_id);
            parent.children = parent.children.filter((c) => c.id !== section.id);
        } else {
            this.state.sections = this.state.sections.filter((s) => s.id !== section.id);
        }

        this.updateSectionSubtotal(section.parent_id || section.id, -section.subtotal);

        if (this.selectedSectionId === sectionId) {
            this.setSelectedSection(this.state.sections[0]?.id || false);
        } else if (sectionId === section.parent_id) {
            this.setSelectedSection(sectionId);
        }
    }

    async duplicateSection(sectionId) {
        const { sections, duplicated_section_id } = await this.orm.call(
            this.orderModel,
            "duplicate_section",
            [this.orderId],
            {
                child_field: this.childField,
                section_id: sectionId,
            }
        );

        this._setSectionsState(sections);
        const duplicatedSection = this._findSectionById(duplicated_section_id);
        if (duplicatedSection.parent_id) {
            this._findSectionById(duplicatedSection.parent_id).isOpen = true;
        }
        this.setSelectedSection(duplicated_section_id);
    }

    async renameSection(sectionId, newName) {
        const name = newName.trim();
        if (!name) {
            this.leaveEditionMode(sectionId);
            return;
        }

        const section = this._findSectionById(sectionId);
        if (!section) {
            return;
        }

        if (sectionId === false) {
            // unsaved section
            const section_data = await this.orm.call(
                this.orderModel,
                "create_section",
                [this.orderId],
                {
                    child_field: this.childField,
                    name: newName,
                    parent_id: section.parent_id,
                }
            );
            Object.assign(section, section_data);
            section.name = newName;
            section.editing = false;
            this.setSelectedSection(section.id);
        } else {
            await this.orm.call(this.orderModel, "rename_section", [this.orderId], {
                child_field: this.childField,
                section_id: sectionId,
                new_name: name,
            });
            section.name = name;
            section.editing = false;
        }
        this.state.editingSectionId = undefined;
    }

    async resequenceSections({ element, parent, previous, next }) {
        const movedSectionId = parseInt(element.dataset.id);
        if (!movedSectionId) {
            return;
        }

        const newParentSectionId = parent ? parseInt(parent.dataset.id) : false;
        const insertAfterSectionId = previous ? parseInt(previous.dataset.id) : false;
        const insertBeforeSectionId = next ? parseInt(next.dataset.id) : null;

        const node = this._findSectionById(movedSectionId);
        if (!node) {
            return;
        }

        if (!!next && !insertBeforeSectionId) {
            // Inserting before the "No Section" section -> do nothing
            return;
        }

        const oldParentSectionId = node.parent_id;

        // Remove the node from its current location before inserting it into the new one.
        if (node.parent_id) {
            const parent = this._findSectionById(node.parent_id);
            const idx = parent.children.findIndex((c) => c.id === movedSectionId);
            parent.children.splice(idx, 1);
        } else {
            const idx = this.state.sections.findIndex((s) => s.id === movedSectionId);
            this.state.sections.splice(idx, 1);
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

        if (oldParentSectionId !== newParentSectionId) {
            if (oldParentSectionId) {
                this.updateSectionSubtotal(oldParentSectionId, -node.subtotal);
            }
            if (newParentSectionId) {
                this.updateSectionSubtotal(newParentSectionId, node.subtotal);
            }
        }

        await this.orm.call(
            this.orderModel,
            "resequence_sections",
            [this.orderId],
            {
                child_field: this.childField,
                moved_section_id: movedSectionId,
                new_parent_section_id: newParentSectionId,
                previous_section_id: insertAfterSectionId,
            }
        );
    }

    updateSectionSubtotal(sectionId, subtotalDelta) {
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
}
