import { useBus } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";

import { Component, onMounted, onWillUpdateProps, onWillStart, useRef, useState } from "@odoo/owl";

//-------------------------------------------------------------------------
// Helpers
//-------------------------------------------------------------------------

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

/**
 * Search panel
 *
 * Represent an extension of the search interface located on the left side of
 * the view. It is divided in sections defined in a "<searchpanel>" node located
 * inside of a "<search>" arch. Each section is represented by a list of different
 * values (categories or ungrouped filters) or groups of values (grouped filters).
 * Its state is directly affected by its model (@see SearchModel).
 */
export class SearchPanel extends Component {
    static template = "web.SearchPanel";
    static props = {
        importedState: { type: String, optional: true },
    };
    static components = {
        Dropdown,
    };
    static subTemplates = {
        section: "web.SearchPanel.Section",
        category: "web.SearchPanel.Category",
        filtersGroup: "web.SearchPanel.FiltersGroup",
    };

    setup() {
        this.state = useState({
            active: {},
            expanded: {},
            showMobileSearch: false,
            sidebarExpanded: true,
        });
        this.root = useRef("root");
        this.scrollTop = 0;
        this.hasImportedState = false;

        this.importState(this.props.importedState);

        useBus(this.env.searchModel, "update", async () => {
            await this.env.searchModel.sectionsPromise;
            this.updateActiveValues();
            this.render();
        });

        onWillStart(async () => {
            await this.env.searchModel.sectionsPromise;
            this.expandDefaultValue();
            this.updateActiveValues();
        });

        onWillUpdateProps(async () => {
            await this.env.searchModel.sectionsPromise;
            this.updateActiveValues();
        });

        onMounted(() => {
            this.updateGroupHeadersChecked();
            if (this.hasImportedState) {
                this.root.el.scroll({ top: this.scrollTop });
            }
        });
    }

    //---------------------------------------------------------------------
    // Getters
    //---------------------------------------------------------------------

    get sections() {
        return this.env.searchModel.getSections((s) => !s.empty);
    }

    //---------------------------------------------------------------------
    // Public
    //---------------------------------------------------------------------

    exportState() {
        const exported = {
            expanded: this.state.expanded,
            scrollTop: this.root.el.scrollTop,
        };
        return JSON.stringify(exported);
    }

    importState(stringifiedState) {
        this.hasImportedState = Boolean(stringifiedState);
        if (this.hasImportedState) {
            const state = JSON.parse(stringifiedState);
            this.state.expanded = state.expanded;
            this.scrollTop = state.scrollTop;
        }
    }

    //---------------------------------------------------------------------
    // Protected
    //---------------------------------------------------------------------

    /**
     * Expands category values holding the default value of a category.
     */
    expandDefaultValue() {
        if (this.hasImportedState) {
            return;
        }
        const categories = this.env.searchModel.getSections((s) => s.type === "category");
        for (const category of categories) {
            this.state.expanded[category.id] = {};
            if (category.activeValueId) {
                const ancestorIds = this.getAncestorValueIds(category, category.activeValueId);
                for (const ancestorId of ancestorIds) {
                    this.state.expanded[category.id][ancestorId] = true;
                }
            }
        }
    }

    /**
     * @param {Object} category
     * @param {number} categoryValueId
     * @returns {number[]} list of ids of the ancestors of the given value in
     *   the given category.
     */
    getAncestorValueIds(category, categoryValueId) {
        const { parentId } = category.values.get(categoryValueId);
        return parentId ? [...this.getAncestorValueIds(category, parentId), parentId] : [];
    }

    /**
     * Returns a formatted version of the active categories to populate
     * the selection banner of the control panel summary.
     * @returns {Object[]}
     */
    getCategorySelection() {
        const activeCategories = this.env.searchModel.getSections(isActiveCategory);
        const selection = [];
        for (const category of activeCategories) {
            const parentIds = this.getAncestorValueIds(category, category.activeValueId);
            const orderedCategoryNames = [...parentIds, category.activeValueId].map(
                (valueId) => category.values.get(valueId).display_name
            );
            selection.push({
                values: orderedCategoryNames,
                icon: category.icon,
                color: category.color,
            });
        }
        return selection;
    }

    /**
     * Returns a formatted version of the active filters to populate
     * the selection banner of the control panel summary.
     * @returns {Object[]}
     */
    getFilterSelection() {
        const filters = this.env.searchModel.getSections(isFilter);
        const selection = [];
        for (const { groups, values, icon, color } of filters) {
            let filterValues;
            if (groups) {
                filterValues = Object.keys(groups)
                    .map((groupId) => nameOfCheckedValues(groups[groupId].values))
                    .flat();
            } else if (values) {
                filterValues = nameOfCheckedValues(values);
            }
            if (filterValues.length) {
                selection.push({ values: filterValues, icon, color });
            }
        }
        return selection;
    }

    /**
     * Checks if the section matching the provided id has at least one active selection.
     * If no id is provided, checks if at least one section has an active selection.
     * @param {Number} sectionId
     */
    hasSelection(sectionId = 0) {
        if (sectionId) {
            const sectionState = this.state.active[sectionId];
            if (sectionState instanceof Object) {
                return Object.values(sectionState).some((val) => val);
            }
            return Boolean(sectionState);
        }
        return Object.keys(this.state.active).some((key) => this.hasSelection(key));
    }

    /**
     * Clears all active selection in the section which id was provided.
     * If no id is provided, clears the selection of all sections.
     * @param {Number} sectionId
     */
    clearSelection(sectionId = 0) {
        const sectionIds = sectionId ? [sectionId] : Object.keys(this.state.active).map(Number);
        this.env.searchModel.clearSections(sectionIds);
    }

    /**
     * Prevent unnecessary calls to the model by ensuring a different category
     * is clicked.
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
        }
        if (category.activeValueId !== value.id) {
            this.env.searchModel.toggleCategoryValue(category.id, value.id);
        }
    }

    toggleSidebar() {
        this.state.sidebarExpanded = !this.state.sidebarExpanded;
    }

    /**
     * @param {number} filterId
     * @param {{ values: Map<Object> }} group
     */
    toggleFilterGroup(filterId, { values }) {
        const valueIds = [];
        const checked = [...values.values()].every(
            (value) => this.state.active[filterId][value.id]
        );
        values.forEach(({ id }) => {
            valueIds.push(id);
            this.state.active[filterId][id] = !checked;
        });
        this.env.searchModel.toggleFilterValues(filterId, valueIds, !checked);
    }

    /**
     * @param {number} filterId
     * @param {Object} [group]
     * @param {number} valueId
     * @param {MouseEvent} ev
     */
    toggleFilterValue(filterId, valueId, { currentTarget }) {
        this.state.active[filterId][valueId] = currentTarget.checked;
        this.updateGroupHeadersChecked();
        this.env.searchModel.toggleFilterValues(filterId, [valueId]);
    }

    updateActiveValues() {
        for (const section of this.sections) {
            if (section.type === "category") {
                this.state.active[section.id] = section.activeValueId;
            } else {
                this.state.active[section.id] = {};
                if (section.groups) {
                    for (const group of section.groups.values()) {
                        for (const value of group.values.values()) {
                            this.state.active[section.id][value.id] = value.checked;
                        }
                    }
                }
                if (section && section.values) {
                    for (const value of section.values.values()) {
                        this.state.active[section.id][value.id] = value.checked;
                    }
                }
            }
        }
    }

    /**
     * Updates the "checked" or "indeterminate" state of each of the group
     * headers according to the state of their values.
     */
    updateGroupHeadersChecked() {
        const groups = document.querySelectorAll(".o_search_panel_filter_group");
        for (const group of groups) {
            const header = group.querySelector(":scope .o_search_panel_group_header input");
            const vals = [...group.querySelectorAll(":scope .o_search_panel_filter_value input")];
            header.checked = false;
            header.indeterminate = false;
            if (vals.every((v) => v.checked)) {
                header.checked = true;
            } else if (vals.some((v) => v.checked)) {
                header.indeterminate = true;
            }
        }
    }

    /**
     * Handles the resize feature on the sidebar
     *
     * @private
     * @param {PointerEvent} ev
     */
    _onStartResize(ev) {
        // Only triggered by left mouse button
        if (ev.button !== 0) {
            return;
        }

        const initialX = ev.pageX;
        const initialWidth = this.root.el.offsetWidth;
        const resizeStoppingEvents = ["keydown", "pointerdown", "pointerup"];

        // Pointermove event : resize header
        const resizePanel = (ev) => {
            ev.preventDefault();
            ev.stopPropagation();
            const maxWidth = Math.max(0.5 * window.innerWidth, initialWidth);
            const delta = ev.pageX - initialX;
            const newWidth = Math.min(maxWidth, Math.max(10, initialWidth + delta));
            this.root.el.style["min-width"] = `${newWidth}px`;
        };
        document.addEventListener("pointermove", resizePanel, true);

        // Pointer or keyboard events : stop resize
        const stopResize = (ev) => {
            // Ignores the initial 'left mouse button down' event in order
            // to not instantly remove the listener
            if (ev.type === "pointerdown" && ev.button === 0) {
                return;
            }
            ev.preventDefault();
            ev.stopPropagation();

            document.removeEventListener("pointermove", resizePanel, true);
            resizeStoppingEvents.forEach((stoppingEvent) => {
                document.removeEventListener(stoppingEvent, stopResize, true);
            });
            // we remove the focus to make sure that the there is no focus inside
            // the panel. If that is the case, there is some css to darken the whole
            // thead, and it looks quite weird with the small css hover effect.
            document.activeElement.blur();
        };
        // We have to listen to several events to properly stop the resizing function. Those are:
        // - pointerdown (e.g. pressing right click)
        // - pointerup : logical flow of the resizing feature (drag & drop)
        // - keydown : (e.g. pressing 'Alt' + 'Tab' or 'Windows' key)
        resizeStoppingEvents.forEach((stoppingEvent) => {
            document.addEventListener(stoppingEvent, stopResize, true);
        });
    }
}
