// @ts-check
/** @odoo-module native */

import {
    Component,
    onWillStart,
    onWillUnmount,
    onWillUpdateProps,
    reactive,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { useSetupAction } from "@web/core/action_hook";
import { browser } from "@web/core/browser/browser";
import { isActivationKey } from "@web/core/browser/hotkeys";
import { SearchModelEvent } from "@web/core/events";
import { exprToBoolean } from "@web/core/utils/format/strings";
import { uniqueId } from "@web/core/utils/functions";
import { useBus } from "@web/core/utils/hooks";

const isFilter = (s) => s.type === "filter";
const isActiveCategory = (s) => s.type === "category" && s.activeValueId;

/**
 * @param {Map<string | false, Object>} values
 * @returns {Object[]}
 */
const nameOfCheckedValues = (values) => {
    const names = [];
    for (const [, value] of values) {
        if (value.checked) {
            names.push(value.display_name);
        }
    }
    return names;
};

export class SearchPanel extends Component {
    static template = "web.SearchPanel";
    static props = {};
    static components = {
        Dropdown,
    };
    static subTemplates = {
        section: "web.SearchPanel.Section",
        category: "web.SearchPanel.Category",
        filtersGroup: "web.SearchPanel.FiltersGroup",
    };

    setup() {
        this.idPrefix = uniqueId("o_sp");
        this.keyExpandSidebar = `search_panel_expanded,${this.env.config.viewId},${this.env.config.actionId}`;
        this.state = useState({
            expanded: {},
            sidebarExpanded: true,
            searchModelUpdates: 0,
        });
        this.hasImportedState = false;
        this.root = useRef("root");
        this.scrollTop = 0;
        this.dropdownStates = {};
        this.width = "10px";

        this.importState(this.env.searchPanelState);
        const sidebarExpandedPreference = browser.localStorage.getItem(
            this.keyExpandSidebar,
        );
        if (sidebarExpandedPreference !== null) {
            this.state.sidebarExpanded = exprToBoolean(sidebarExpandedPreference);
        }

        useBus(this.env.searchModel, SearchModelEvent.UPDATE, async () => {
            await this.env.searchModel.sectionsPromise;
            this.updateActiveValues();
            this.state.searchModelUpdates++;
        });

        useEffect(
            (el) => {
                if (el && this.hasImportedState) {
                    el.style["min-width"] = this.width;
                    el.scroll({ top: this.scrollTop });
                }
            },
            () => [this.root.el],
        );

        useSetupAction({
            getGlobalState: () => ({
                searchPanel: this.exportState(),
            }),
        });

        onWillStart(async () => {
            await this.env.searchModel.sectionsPromise;
            this.expandDefaultValue();
            this.expandValues();
            this.updateActiveValues();
        });

        onWillUpdateProps(async () => {
            await this.env.searchModel.sectionsPromise;
            this.updateActiveValues();
        });

        onWillUnmount(() => {
            this._removeResizeListeners?.();
        });
    }

    /** @returns {Object[]} */
    get sections() {
        void this.state.searchModelUpdates;
        return this.env.searchModel.getSections((s) => !s.empty);
    }

    /** @returns {string} */
    exportState() {
        const exported = {
            expanded: this.state.expanded,
            scrollTop: this.root.el?.scrollTop || 0,
            sidebarExpanded: this.state.sidebarExpanded,
            width: this.width,
        };
        return JSON.stringify(exported);
    }

    /** @param {Object|null} state */
    importState(state) {
        this.hasImportedState = Boolean(state);
        if (this.hasImportedState) {
            this.state.expanded = state.expanded;
            this.scrollTop = state.scrollTop;
            this.state.sidebarExpanded = state.sidebarExpanded;
            this.width = state.width;
        }
    }

    /**
     * @param {number} sectionId
     * @returns {{ isOpen: boolean, open: Function, close: Function }}
     */
    getDropdownState(sectionId) {
        if (!this.dropdownStates[sectionId]) {
            const state = reactive({
                isOpen: false,
                open: () => (state.isOpen = true),
                close: () => (state.isOpen = false),
            });
            this.dropdownStates[sectionId] = state;
        }
        return this.dropdownStates[sectionId];
    }

    initExpansionState() {
        for (const category of this.env.searchModel.getSections(
            (s) => s.type === "category",
        )) {
            this.state.expanded[category.id] ??= {};
        }
    }

    expandDefaultValue() {
        this.initExpansionState();
        if (this.hasImportedState) {
            return;
        }
        const categories = this.env.searchModel.getSections(
            (s) => s.type === "category",
        );
        for (const category of categories) {
            if (category.activeValueId) {
                const ancestorIds = this.getAncestorValueIds(
                    category,
                    category.activeValueId,
                );
                for (const ancestorId of ancestorIds) {
                    this.state.expanded[category.id][ancestorId] = true;
                }
            }
        }
    }

    expandValues() {
        if (this.hasImportedState) {
            return;
        }
        const categories = this.env.searchModel.getSections(
            (s) => s.type === "category",
        );
        for (const category of categories) {
            if (category.depth === 0) {
                continue;
            }

            const expand = (id, level) => {
                const value = category.values.get(id);
                if (!level || !value) {
                    return;
                }
                this.state.expanded[category.id][id] = true;
                level -= 1;
                for (const childId of value.childrenIds) {
                    expand(childId, level);
                }
            };

            for (const rootId of category.rootIds) {
                expand(rootId, category.depth);
            }
        }
    }

    /**
     * @param {Object} category
     * @param {number} categoryValueId
     * @returns {number[]}
     */
    getAncestorValueIds(category, categoryValueId) {
        const ancestorIds = [];
        const seen = new Set([categoryValueId]);
        let { parentId } = category.values.get(categoryValueId) || {};
        while (parentId && !seen.has(parentId)) {
            const parent = category.values.get(parentId);
            if (!parent) {
                break;
            }
            ancestorIds.unshift(parentId);
            seen.add(parentId);
            ({ parentId } = parent);
        }
        return ancestorIds;
    }

    /** @returns {Object[]} */
    getCategorySelection() {
        const activeCategories = this.env.searchModel.getSections(isActiveCategory);
        const selection = [];
        for (const category of activeCategories) {
            const parentIds = this.getAncestorValueIds(
                category,
                category.activeValueId,
            );
            const orderedCategoryNames = [...parentIds, category.activeValueId].map(
                (valueId) => category.values.get(valueId).display_name,
            );
            selection.push({
                values: orderedCategoryNames,
                icon: category.icon,
                color: category.color,
            });
        }
        return selection;
    }

    /** @returns {Object[]} */
    getFilterSelection() {
        const filters = this.env.searchModel.getSections(isFilter);
        const selection = [];
        for (const { groups, values, icon, color } of filters) {
            const filterValues = groups
                ? [...groups.values()].flatMap((group) =>
                      nameOfCheckedValues(group.values),
                  )
                : nameOfCheckedValues(values);
            if (filterValues.length) {
                selection.push({ values: filterValues, icon, color });
            }
        }
        return selection;
    }

    /**
     * @param {Object} section
     * @returns {boolean}
     */
    isSelected(section) {
        if (section.type === "category") {
            return Boolean(section.activeValueId);
        }
        return [...section.values.values()].some((value) => value.checked);
    }

    /** @param {Number} sectionId */
    hasSelection(sectionId = 0) {
        const sections = sectionId
            ? this.env.searchModel.getSections((s) => s.id === sectionId)
            : this.sections;
        return sections.some((section) => this.isSelected(section));
    }

    /** @param {Number} sectionId */
    clearSelection(sectionId = 0) {
        const sectionIds = sectionId
            ? [sectionId]
            : this.sections.map((section) => section.id);
        this.env.searchModel.clearSections(sectionIds);
    }

    /**
     * @param {Object} category
     * @param {Object} value
     */
    async toggleCategory(category, value) {
        if (value.childrenIds.length) {
            const categoryState = this.state.expanded[category.id];
            if (categoryState[value.id] && category.activeValueId === value.id) {
                delete categoryState[value.id];
            } else {
                categoryState[value.id] = true;
            }
        } else {
            this.getDropdownState(category.id).close();
        }
        if (category.activeValueId !== value.id) {
            this.env.searchModel.toggleCategoryValue(category.id, value.id);
        }
    }

    /**
     * @param {KeyboardEvent} ev
     * @param {Object} category
     * @param {Object} value
     */
    onCategoryKeydown(ev, category, value) {
        if (!isActivationKey(ev)) {
            return;
        }
        ev.preventDefault();
        this.toggleCategory(category, value);
    }

    /**
     * @param {Object} category
     * @param {Object} value
     * @returns {string|false}
     */
    categoryAriaExpanded(category, value) {
        if (!value.childrenIds.length) {
            return false;
        }
        return this.state.expanded[category.id][value.id] ? "true" : "false";
    }

    toggleSidebar() {
        this._sidebarAutoCollapsed = false;
        this.state.sidebarExpanded = !this.state.sidebarExpanded;
        browser.localStorage.setItem(
            this.keyExpandSidebar,
            /** @type {any} */ (this.state.sidebarExpanded),
        );
    }

    /**
     * @param {number} filterId
     * @param {{ values: Map<any, Object> }} group
     */
    toggleFilterGroup(filterId, { values }) {
        const checked = [...values.values()].every((value) => value.checked);
        this.env.searchModel.toggleFilterValues(filterId, [...values.keys()], !checked);
    }

    /**
     * @param {number} filterId
     * @param {number} valueId
     */
    toggleFilterValue(filterId, valueId) {
        this.env.searchModel.toggleFilterValues(filterId, [valueId]);
    }

    /**
     * @param {{ values: Map<any, Object> }} group
     * @returns {{ checked: boolean, indeterminate: boolean }}
     */
    getGroupState({ values }) {
        let checkedCount = 0;
        for (const value of values.values()) {
            if (value.checked) {
                checkedCount++;
            }
        }
        return {
            checked: checkedCount > 0 && checkedCount === values.size,
            indeterminate: checkedCount > 0 && checkedCount < values.size,
        };
    }

    updateActiveValues() {
        if (!this.sections.length) {
            if (this.state.sidebarExpanded) {
                this._sidebarAutoCollapsed = true;
                this.state.sidebarExpanded = false;
            }
        } else if (this._sidebarAutoCollapsed) {
            this._sidebarAutoCollapsed = false;
            this.state.sidebarExpanded = true;
        }
    }

    /**
     * @private
     * @param {PointerEvent} ev
     */
    _onStartResize(ev) {
        if (ev.button !== 0) {
            return;
        }

        const initialX = ev.pageX;
        const initialWidth = this.root.el.offsetWidth;
        const resizeStoppingEvents = ["keydown", "pointerdown", "pointerup"];

        const removeListeners = () => {
            document.removeEventListener("pointermove", resizePanel, true);
            resizeStoppingEvents.forEach((stoppingEvent) => {
                document.removeEventListener(stoppingEvent, stopResize, true);
            });
            this._removeResizeListeners = null;
        };
        this._removeResizeListeners = removeListeners;

        const resizePanel = (ev) => {
            if (!this.root.el) {
                removeListeners();
                return;
            }
            ev.preventDefault();
            ev.stopPropagation();
            const maxWidth = Math.max(0.5 * window.innerWidth, initialWidth);
            const delta = ev.pageX - initialX;
            const newWidth = Math.min(maxWidth, Math.max(10, initialWidth + delta));
            this.width = `${newWidth}px`;
            this.root.el.style["min-width"] = this.width;
        };
        document.addEventListener("pointermove", resizePanel, true);

        const stopResize = (ev) => {
            if (ev.type === "pointerdown" && ev.button === 0) {
                return;
            }
            ev.preventDefault();
            ev.stopPropagation();

            removeListeners();
            const active = /** @type {HTMLElement} */ (document.activeElement);
            if (active && this.root.el?.contains(active)) {
                active.blur();
            }
        };
        resizeStoppingEvents.forEach((stoppingEvent) => {
            document.addEventListener(stoppingEvent, stopResize, true);
        });
    }
}
