import { onWillStart, proxy } from '@odoo/owl';
import { getActiveHotkey } from '@web/core/hotkeys/hotkey_service';
import { rpc } from '@web/core/network/rpc';
import { useBus } from '@web/core/utils/hooks';
import { useNestedSortable } from "@web/core/utils/nested_sortable";
import { useRef, useSubEnv } from "@web/owl2/utils";
import { SearchPanel } from '@web/search/search_panel/search_panel';
import { SectionRow } from './section_row';

export class AccountProductCatalogSearchPanel extends SearchPanel {
    static template = 'account.ProductCatalogSearchPanel';
    static components = {
        SectionRow,
    };

    setup() {
        super.setup();

        this.state = proxy({
            ...this.state,
            sections: [],
            isAddingSection: '',
            newSectionName: "",
            dragging: false,
        });

        useSubEnv({
            setSelectedSection: this.setSelectedSection.bind(this),
            enableSectionInput: this.enableSectionInput.bind(this),
            createSection: this.createSection.bind(this),
            loadSections: this.loadSections.bind(this),
            onSectionInputKeydown: this.onSectionInputKeydown.bind(this),
            _findSectionById: this._findSectionById.bind(this),
            _getSectionInfoParams: this._getSectionInfoParams.bind(this),
            _sortSectionsBySequence : this._sortSectionsBySequence.bind(this),
        })

        useBus(this.env.searchModel, 'section-line-count-change', this.updateSectionLineCount);

        onWillStart(async () => await this.loadSections());

        this.mainTree = useRef("mainTree");

         useNestedSortable({
            ref: this.mainTree,
            elements: "li.o_section",
            nest: true,
            listTagName: "ul",
            useElementSize: true,
            maxLevels: 2,
            preventDrag: (el) => {
                const id = el.dataset.id;
                return !id;
            },
            isAllowed: (ctx) => {
                const placeholder = ctx.placeHolder;

                const parent = placeholder.parentElement?.closest("li.o_section");
                const next = placeholder.nextElementSibling;

                if (parent && !parent.dataset.id) {
                    return false;
                }

                if (next && !next.dataset.id) {
                    return false;
                }

                return true;
            },

            onDragStart: () => {
                this.state.dragging = true;
            },

            onDragEnd: () => {
                this.state.dragging = false;
            },

            onDrop: (params) => this._handleDrop(params),

        });
    }

     _handleDrop({ element, parent, next }) {
        const movedId = parseInt(element.dataset.id);
        if (!movedId) return;
        const newParentId = parent
            ? parseInt(parent.dataset.id)
            : false;

        const nextId = next
            ? parseInt(next.dataset.id)
            : null;

        this._moveNode(movedId, newParentId, nextId);
    }

    _moveNode(movedId, newParentId, nextId) {
        // 1. Remove node from old location
        const node = this._extractNode(movedId, this.state.sections);
        if (!node) return;

        // 2. Update parent
        node.parent_id = newParentId;

        // 3. Get target list
        const targetList = newParentId
            ? this._findSectionById(newParentId, this.state.sections).children
            : this.state.sections;

        // 4. Compute insert index (based on NEXT)
        let insertIndex = targetList.length;

        if (nextId !== null) {
            const idx = targetList.findIndex(n => n.id === nextId);
            if (idx !== -1) {
                insertIndex = idx;
            }
        }

        // 5. Insert node
        targetList.splice(insertIndex, 0, node);

        // 6. Resequence ONLY siblings
        this._resequence(targetList);

        // 7. Trigger OWL re-render
        this.state.sections = [...this.state.sections];

        this._syncMove(movedId, newParentId, nextId);
    }

    _extractNode(id, nodes) {
        for (let i = 0; i < nodes.length; i++) {
            const node = nodes[i];

            if (node.id === id) {
                return nodes.splice(i, 1)[0];
            }

            const found = this._extractNode(id, node.children);
            if (found) return found;
        }
    }

    _resequence(nodes) {
        for (let i = 0; i < nodes.length; i++) {
            nodes[i].sequence = i + 1;
        }
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

    enableSectionInput(type, parentId = null) {
        this.state.isAddingSection = parentId
            ? `subsection_${parentId}`
            : type;
        setTimeout(() => document.querySelector('.o_section_input')?.focus(), 100);
    }

    onSectionInputKeydown(ev, parentId) {
        const hotkey = getActiveHotkey(ev);
        if (hotkey === 'enter') {
            this.createSection(parentId);
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

    async createSection(parentId = null) {
        const sectionName = this.state.newSectionName.trim();
        if (!sectionName) return this.state.isAddingSection = '';

        const position = this.state.isAddingSection;
        const section = await rpc('/product/catalog/create_section',
            this._getSectionInfoParams({
                name: sectionName,
                position: position,
                parent_id: parentId,
            })
        );

        if (section) {
            let newLineCount = 0;

            if (position === 'top') {
                const noSection = this.state.sections.find(sec => sec.id === false);

                if (noSection) {
                    newLineCount = noSection.line_count;
                    this.state.sections = this.state.sections.filter(sec => sec.id !== false);
                }
            }
            const newNode = {
                ...section,
                name: sectionName,
                children: [],
                isOpen: true,
                parent_id: parentId,
                line_count: newLineCount
            };

            if (parentId) {
                const parent = this._findSectionById(parentId, this.state.sections);
                parent.children.push(newNode);
                parent.isOpen = true;
            } else {
                this.state.sections.push(newNode);
            }
            this._sortSectionsBySequence(this.state.sections);
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

        const map = new Map();
        const tree = [];
         for (const sec of sections) {
            map.set(sec.id, {
                ...sec,
                children: [],
                isOpen: false,
            });
        }
        for (const sec of map.values()) {
            if (sec.parent_id) {
                map.get(sec.parent_id)?.children.push(sec);
            } else {
                tree.push(sec);
            }
        }

        this.state.sections = tree;
        if (tree.length) {
            this.setSelectedSection(tree[0].id);
        }
    }

    async _syncMove(id, parent_id, before_id) {
        await rpc(
            "/product/catalog/resequence_sections",
            this._getSectionInfoParams({
                id,
                parent_id,
                before_id,
            })
        );
    }

    updateSectionLineCount({ detail: { sectionId, lineCountChange } }) {
        const section = this._findSectionById(sectionId, this.state.sections);
        if (!section) return;

        section.line_count = Math.max(0, (section.line_count || 0) + lineCountChange);

        if (section.line_count === 0 && sectionId === false && this.state.sections.length > 1) {
            this.state.sections = this.state.sections.filter(sec => sec.id !== sectionId);
            this.setSelectedSection(this.state.sections.length ? this.state.sections[0].id : null);
        }
    }

    _findSectionById(id, nodes) {
        for (const node of nodes) {
            if (node.id === id) return node;
            const found = this._findSectionById(id, node.children);
            if (found) return found;
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
        const sortRecursively = (nodes) => {
            nodes.sort((a, b) => a.sequence - b.sequence);
            for (const node of nodes) {
                if (node.children && node.children.length) {
                    sortRecursively(node.children);
                }
            }
        };

        sortRecursively(sections);
        this.state.sections = sections;
    }
}
