/** @odoo-module alias=web.PivotRenderer **/

    import { useEffect } from "@web/core/utils/hooks";
    import OwlAbstractRenderer from '../abstract_renderer_owl';
    import field_utils from 'web.field_utils';
    import { DEFAULT_INTERVAL, INTERVAL_OPTIONS, getIntervalOptions } from 'web.searchUtils';

    const { Component, hooks } = owl;
    const { useExternalListener, useState } = hooks;

    class PivotCustomGroupByItem extends Component {
        constructor() {
            super(...arguments);
            this.canBeOpened = true;
            this.state = useState({ fieldName: this.props.fields[0].name });
        }

        //---------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------

        /**
         * @private
         */
        onApply() {
            const { fieldName } = this.state;
            const { type } = this.props.fields.find(f => f.name === fieldName);
            let interval = null;
            if (['date', 'datetime'].includes(type)) {
                interval = DEFAULT_INTERVAL;
            }
            this.trigger('groupby-menu-selection', { fieldName, interval, custom: true });
            this.state.open = false;
        }
    }

    PivotCustomGroupByItem.template = "web.CustomGroupByItem";
    PivotCustomGroupByItem.props = { fields: Array };

    export class PivotGroupByMenu extends Component {

        constructor() {
            super(...arguments);
            this.intervalOptions = INTERVAL_OPTIONS;
            this.openedSubMenus = {};
        }

        //---------------------------------------------------------------------
        // Getters
        //---------------------------------------------------------------------

        /**
         * @override
         */
        get items() {
            let items = this.props.fields;
            if (this.props.hasSearchArchGroupBys) {
                items = this.props.searchModel.get('filters', f => f.type === 'groupBy');
                let groupNumber = 1 + Math.max(...items.map(g => g.groupNumber), 0);
                for (const [_, customGroupBy] of this.props.customGroupBys) {
                    customGroupBy.groupNumber = groupNumber++;
                    items.push(customGroupBy);
                }
            }
            return items.map((item) => ({
                ...item,
                id: item.id || item.name,
                fieldName: item.fieldName || item.name,
                description: item.description || item.string,
                isActive: false,
                options:
                    item.options || ["date", "datetime"].includes(item.type)
                        ? getIntervalOptions()
                        : undefined,
            }));
        }

        //---------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------

        /**
         * @param {string} fieldName
         * @param {string|null} interval
        */
        _onClickMenuGroupBy(fieldName, interval) {
            this.trigger('groupby-menu-selection', { fieldName, interval });
        }

        _toggleMenu(id) {
            this.openedSubMenus[id] = !this.openedSubMenus[id];
            this.render();
        }
    }

    PivotGroupByMenu.template = "web.legacy.PivotGroupByMenu";
    PivotGroupByMenu.components = { PivotCustomGroupByItem };
    PivotGroupByMenu.props = {
        customGroupBys: Map,
        fields: Object,
        hasSearchArchGroupBys: Boolean,
        searchModel: true,
    };

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

            const searchArchGroupBys = this.props.searchModel.get(
                'filters',
                f => f.type === 'groupBy' && !f.custom
            );
            // searchArchGroupBys is not an array when the control panel model
            // extension is not installed (e.g. in an embedded pivot view)
            this.hasSearchArchGroupBys = Boolean(searchArchGroupBys && searchArchGroupBys.length);
            this.customGroupBys = new Map();

            useEffect(() => this._updateTooltip());
            useExternalListener(window, 'click', this._resetState);
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

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
         * @private
         * @param {OwlEvent} ev
         */
        _onGroupByMenuSelection(ev) {
            if (this.hasSearchArchGroupBys) {
                const { custom, fieldName } = ev.detail;
                if (custom && !this.customGroupBys.has(fieldName)) {
                    const field = this.props.groupableFields.find(g => g.fieldName === fieldName)
                    this.customGroupBys.set(fieldName, field);
                }
            }
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
            this.trigger(cell.isLeaf ? 'closed_header_click' : 'opened_header_click', { cell, type });
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

    PivotRenderer.template = 'web.legacy.PivotRenderer';
    PivotRenderer.components = { PivotGroupByMenu };

    export default PivotRenderer;
