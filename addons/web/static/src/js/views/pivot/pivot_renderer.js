odoo.define('web.PivotRenderer', function (require) {
    "use strict";

    const OwlAbstractRenderer = require('web.AbstractRendererOwl');
    const field_utils = require('web.field_utils');
    const patchMixin = require('web.patchMixin');

    const { useExternalListener, useState, onMounted, onPatched } = owl.hooks;

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

            onMounted(() => this._updateTooltip());

            onPatched(() => this._updateTooltip());

            if (!this.env.device.isMobile) {
                useExternalListener(window, 'click', this._resetState);
            }
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

    PivotRenderer.template = 'web.PivotRenderer';

    return patchMixin(PivotRenderer);

});
