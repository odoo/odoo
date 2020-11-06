/** @odoo-module alias=web.PivotRenderer **/

    const GroupByMenu = require('web.GroupByMenu');
    const CustomGroupByItem = require('web.CustomGroupByItem');
    const OwlAbstractRenderer = require('web.AbstractRendererOwl');
    const field_utils = require('web.field_utils');

    const { useExternalListener, useState, useSubEnv, onMounted, onPatched } = owl.hooks;

    class PivotCustomGroupByItem extends CustomGroupByItem {
        //---------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------

        /**
         * @private
         */
        _onApply() {
            const field = this.props.fields.find(f => f.name === this.state.fieldName);
            this.model.dispatch('createNewGroupBy', field, true);
            this.state.open = false;
        }
    }

    class PivotGroupByMenu extends GroupByMenu {

        //---------------------------------------------------------------------
        // Getters
        //---------------------------------------------------------------------

        /**
         * @override
         */
        get items() {
            const items = this.model.get('filters', f => f.type === 'groupBy');
            items.forEach(item => {
                if (this.props.activeGroupBys.includes(item.fieldName)) {
                    item.isActive = true;
                }
            });
            return items;
        }

        //----------------------------------------------------------------------
        // Handlers
        //----------------------------------------------------------------------

        /**
         * @private
         * @param {OwlEvent} ev
         */
        _onItemSelected(ev) {
            const { item, interval } = ev.detail;
            const field = {
                name: item.fieldName,
            };
            this.trigger('groupby_menu_selection', { field, interval });
            super._onItemSelected(...arguments);
        }
    }
    PivotGroupByMenu.template = "web.PivotGroupByMenu";
    PivotGroupByMenu.components = { PivotCustomGroupByItem };
    PivotGroupByMenu.props = Object.assign({}, GroupByMenu.props, {
        fields: Object,
        activeGroupBys: Array,
    });

    /**
     * Here is a basic example of the structure of the Pivot Table:
     *
     * ┌─────────────────────────┬─────────────────────────────────────────────┬─────────────────┐
     * │                         │ - web.PivotHeader                           │                 │
     * │                         ├──────────────────────┬──────────────────────┤                 │
     * │                         │ + web.PivotHeader    │ + web.PivotHeader    │                 │
     * ├─────────────────────────┼──────────────────────┼──────────────────────┼─────────────────┤
     * │                         │ web.PivotMeasure     │ web.PivotMeasure     │                 │
     * ├─────────────────────────┼──────────────────────┼──────────────────────┼─────────────────┤
     * │ ─ web.PivotHeader       │                      │                      │                 │
     * ├─────────────────────────┼──────────────────────┼──────────────────────┼─────────────────┤
     * │    + web.PivotHeader    │                      │                      │                 │
     * ├─────────────────────────┼──────────────────────┼──────────────────────┼─────────────────┤
     * │    + web.PivotHeader    │                      │                      │                 │
     * └─────────────────────────┴──────────────────────┴──────────────────────┴─────────────────┘
     *
     */

    class PivotRenderer extends OwlAbstractRenderer {
        /**
         * @override
         * @param {boolean} props.disableLinking Disallow opening records by clicking on a cell
         * @param {Object} props.widgets Widgets defined in the arch
         */
        constructor() {
            super(...arguments);
            this.sampleDataTargets = ['table'];
            this.state = useState({
                activeNodeHeader: {
                    groupId: false,
                    isXAxis: false,
                    click: false
                },
            });

            useSubEnv({
                searchModel: this.props.searchModel,
            });
            this.hasSearchGroups = this.props.searchModel.get('filters', f => f.type === 'groupBy' && !f.customGroup);
            this.customGroupableFields = this._formatFields(this.props.fields);

            onMounted(() => this._updateTooltip());

            onPatched(() => this._updateTooltip());

            useExternalListener(window, 'click', this._resetState);
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * Give `name` and `description` keys to the fields given to the control
         * panel.
         * @private
         * @param {Object} fields
         * @returns {Object}
         */
        _formatFields(fields) {
            const formattedFields = {};
            for (const fieldName in fields) {
                formattedFields[fieldName] = Object.assign({
                    description: fields[fieldName].string,
                    name: fieldName,
                }, fields[fieldName]);
            }
            return formattedFields;
        }
        /**
         * Get the formatted value of the cell
         *
         * @private
         * @param {Object} cell
         * @returns {string} Formatted value
         */
        _getFormattedValue(cell) {
            const type = this.props.widgets[cell.measure] ||
                (this.props.fields[cell.measure].type === 'many2one' ? 'integer' : this.props.fields[cell.measure].type);
            const formatter = field_utils.format[type];
            return formatter(cell.value, this.props.fields[cell.measure]);
        }

        /**
         * Get the formatted variation of a cell
         *
         * @private
         * @param {Object} cell
         * @returns {string} Formatted variation
         */
        _getFormattedVariation(cell) {
            const value = cell.value;
            return isNaN(value) ? '-' : field_utils.format.percentage(value, this.props.fields[cell.measure]);
        }

        /**
         * Retrieves the padding of a left header
         *
         * @private
         * @param {Object} cell
         * @returns {Number} Padding
         */
        _getPadding(cell) {
            return 5 + cell.indent * 30;
        }

        /**
         * Compute if a cell is active (with its groupId)
         *
         * @private
         * @param {Array} groupId GroupId of a cell
         * @param {Boolean} isXAxis true if the cell is on the x axis
         * @returns {Boolean} true if the cell is active
         */
        _isClicked(groupId, isXAxis) {
            return _.isEqual(groupId, this.state.activeNodeHeader.groupId) && this.state.activeNodeHeader.isXAxis === isXAxis;
        }

        /**
         * Reset the state of the node.
         *
         * @private
         */
        _resetState() {
            // This check is used to avoid the destruction of the dropdown.
            // The click on the header bubbles to window in order to hide
            // all the other dropdowns (in this component or other components).
            // So we need isHeaderClicked to cancel this behaviour.
            if (this.isHeaderClicked) {
                this.isHeaderClicked = false;
                return;
            }
            this.state.activeNodeHeader = {
                groupId: false,
                isXAxis: false,
                click: false
            };
        }

        /**
         * Configure the tooltips on the headers.
         *
         * @private
         */
        _updateTooltip() {
            $(this.el).find('.o_pivot_header_cell_opened, .o_pivot_header_cell_closed').tooltip();
        }

        //----------------------------------------------------------------------
        // Handlers
        //----------------------------------------------------------------------


        /**
         * Handles a click on a menu item in the dropdown to select a groupby.
         *
         * @private
         * @param {Object} field
         * @param {string} interval
         */
        _onClickMenuGroupBy(field, interval) {
            this.trigger('groupby_menu_selection', { field, interval });
        }


        /**
         * Handles a click on a header node
         *
         * @private
         * @param {Object} cell
         * @param {string} type col or row
         */
        _onHeaderClick(cell, type) {
            const groupValues = cell.groupId[type === 'col' ? 1 : 0];
            const groupByLength = type === 'col' ? this.props.colGroupBys.length : this.props.rowGroupBys.length;
            if (cell.isLeaf && groupValues.length >= groupByLength) {
                this.isHeaderClicked = true;
                this.state.activeNodeHeader = {
                    groupId: cell.groupId,
                    isXAxis: type === 'col',
                    click: 'leftClick'
                };
            }
            // when opened header is closed then grouping will be removed from pivot groupbys(col/row/extended groupbys)
            // callback will be called from opened_header_click handler, it is called to toggle those
            // groups which are active inside search groupby but we collpse it from pivot view
            const updatePivotGroupBy = () => {
                this.props.activeGroupBys;
                this.pivotGroupBy;
                if (this.hasSearchGroups) {
                    const searchGroupBys = this.props.searchModel.get('filters', f => f.type === 'groupBy');
                    searchGroupBys.forEach(group => {
                        if (group.isActive && !this.props.activeGroupBys.includes(group.fieldName)) {
                            // TODO: Do not call rpc when toggling filter here as we do not want trigger query here
                            // pivot reads data for itself
                            this.props.searchModel.dispatch('toggleFilter', group.id);
                        }
                    });
                }
            };
            this.trigger(cell.isLeaf ? 'closed_header_click' : 'opened_header_click', { cell, type, callback: updatePivotGroupBy });
        }

        /**
         * Hover the column in which the mouse is.
         *
         * @private
         * @param {MouseEvent} ev
         */
        _onMouseEnter(ev) {
            var index = [...ev.currentTarget.parentNode.children].indexOf(ev.currentTarget);
            if (ev.currentTarget.tagName === 'TH') {
                index += 1;
            }
            this.el.querySelectorAll('td:nth-child(' + (index + 1) + ')').forEach(elt => elt.classList.add('o_cell_hover'));
        }

        /**
         * Remove the hover on the columns.
         *
         * @private
         */
        _onMouseLeave() {
            this.el.querySelectorAll('.o_cell_hover').forEach(elt => elt.classList.remove('o_cell_hover'));
        }
    }

    PivotRenderer.template = 'web.PivotRenderer';
    PivotRenderer.components = {
        PivotGroupByMenu,
    };

    export default PivotRenderer;
