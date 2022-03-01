/** @odoo-module alias=web.searchPanel **/

    import { Model, useModel } from "web.Model";
    import { LegacyComponent } from "@web/legacy/legacy_component";

    const { onMounted, onWillStart, onWillUpdateProps, useRef, useState, useSubEnv } = owl;

    /**
     * Search panel
     *
     * Represent an extension of the search interface located on the left side of
     * the view. It is divided in sections defined in a "<searchpanel>" node located
     * inside of a "<search>" arch. Each section is represented by a list of different
     * values (categories or ungrouped filters) or groups of values (grouped filters).
     * Its state is directly affected by its model (@see SearchPanelModelExtension).
     * @extends Component
     */
    class SearchPanel extends LegacyComponent {
        setup() {
            useSubEnv({ searchModel: this.props.searchModel });

            this.state = useState({
                active: {},
                expanded: {},
            });
            this.model = useModel("searchModel");
            this.scrollTop = 0;
            this.hasImportedState = false;

            this.importState(this.props.importedState);

            this.legacySearchPanelRef = useRef("legacySearchPanel");

            onWillStart(async () => {
                this._expandDefaultValue();
                this._updateActiveValues();
            });

            onMounted(() => {
                this._updateGroupHeadersChecked();
                if (this.hasImportedState && this.legacySearchPanelRef.el) {
                    this.legacySearchPanelRef.el.scroll({ top: this.scrollTop });
                }
            });

            onWillUpdateProps(async () => {
                this._updateActiveValues();
            });
        }

        //---------------------------------------------------------------------
        // Getters
        //---------------------------------------------------------------------

        get sections() {
            return this.model.get("sections", s => !s.empty);
        }

        //---------------------------------------------------------------------
        // Public
        //---------------------------------------------------------------------

        exportState() {
            const exported = {
                expanded: this.state.expanded,
                scrollTop: this.legacySearchPanelRef.el ? this.legacySearchPanelRef.el.scrollTop : 0,
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
        // Private
        //---------------------------------------------------------------------

        /**
         * Expands category values holding the default value of a category.
         * @private
         */
        _expandDefaultValue() {
            if (this.hasImportedState) {
                return;
            }
            const categories = this.model.get("sections", s => s.type === "category");
            for (const category of categories) {
                this.state.expanded[category.id] = {};
                if (category.activeValueId) {
                    const ancestorIds = this._getAncestorValueIds(category, category.activeValueId);
                    for (const ancestorId of ancestorIds) {
                        this.state.expanded[category.id][ancestorId] = true;
                    }
                }
            }
        }

        /**
         * @private
         * @param {Object} category
         * @param {number} categoryValueId
         * @returns {number[]} list of ids of the ancestors of the given value in
         *   the given category.
         */
        _getAncestorValueIds(category, categoryValueId) {
            const { parentId } = category.values.get(categoryValueId);
            return parentId ? [...this._getAncestorValueIds(category, parentId), parentId] : [];
        }

        /**
         * Prevent unnecessary calls to the model by ensuring a different category
         * is clicked.
         * @private
         * @param {Object} category
         * @param {Object} value
         */
        async _toggleCategory(category, value) {
            if (value.childrenIds.length) {
                const categoryState = this.state.expanded[category.id];
                if (categoryState[value.id] && category.activeValueId === value.id) {
                    delete categoryState[value.id];
                } else {
                    categoryState[value.id] = true;
                }
            }
            if (category.activeValueId !== value.id) {
                this.state.active[category.id] = value.id;
                this.model.dispatch("toggleCategoryValue", category.id, value.id);
            }
        }

        /**
         * @private
         * @param {number} filterId
         * @param {{ values: Map<Object> }} group
         */
        _toggleFilterGroup(filterId, { values }) {
            const valueIds = [];
            const checked = [...values.values()].every(
                (value) => this.state.active[filterId][value.id]
            );
            values.forEach(({ id }) => {
                valueIds.push(id);
                this.state.active[filterId][id] = !checked;
            });
            this.model.dispatch("toggleFilterValues", filterId, valueIds, !checked);
        }

        /**
         * @private
         * @param {number} filterId
         * @param {Object} [group]
         * @param {number} valueId
         * @param {MouseEvent} ev
         */
        _toggleFilterValue(filterId, valueId, { currentTarget }) {
            this.state.active[filterId][valueId] = currentTarget.checked;
            this._updateGroupHeadersChecked();
            this.model.dispatch("toggleFilterValues", filterId, [valueId]);
        }

        _updateActiveValues() {
            for (const section of this.model.get("sections")) {
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
         * @private
         */
        _updateGroupHeadersChecked() {
            if (!this.legacySearchPanelRef.el) {
                return;
            }
            const groups = this.legacySearchPanelRef.el.querySelectorAll(":scope .o_search_panel_filter_group");
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
    }
    SearchPanel.modelExtension = "SearchPanel";

    SearchPanel.props = {
        className: { type: String, optional: 1 },
        importedState: { type: String, optional: 1 },
        searchModel: Model,
    };
    SearchPanel.template = "web.Legacy.SearchPanel";

    export default SearchPanel;
