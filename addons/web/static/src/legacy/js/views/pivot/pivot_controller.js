/** @odoo-module alias=web.PivotController **/

    /**
     * Odoo Pivot Table Controller
     *
     * This class is the Controller for the pivot table view.  It has to coordinate
     * the actions coming from the search view (through the update method), from
     * the renderer, from the model, and from the control panel.
     *
     * It can display action buttons in the control panel, to select a different
     * measure, or to perform some other actions such as download/expand/flip the
     * view.
     */

    import AbstractController from '../abstract_controller';
    import core from 'web.core';
    import framework from 'web.framework';
    import session from 'web.session';

    const _t = core._t;
    const QWeb = core.qweb;

    const PivotController = AbstractController.extend({
        custom_events: Object.assign({}, AbstractController.prototype.custom_events, {
            closed_header_click: '_onClosedHeaderClicked',
            open_view: '_onOpenView',
            opened_header_click: '_onOpenedHeaderClicked',
            sort_rows: '_onSortRows',
            groupby_menu_selection: '_onGroupByMenuSelection',
        }),

        /**
         * @override
         * @param parent
         * @param model
         * @param renderer
         * @param {Object} params
         */
        init: function (parent, model, renderer, params) {
            this._super(...arguments);

            this.disableLinking = params.disableLinking;
            this.measures = params.measures;
            this.title = params.title;
            // views to use in the action triggered when a data cell is clicked
            this.views = params.views;
            this.groupSelected = null;
        },
        /**
         * @override
         */
        destroy: function () {
            if (this.$buttons) {
                // remove jquery's tooltip() handlers
                this.$buttons.find('button').off();
            }
            return this._super(...arguments);
        },

        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------

        /**
         * Returns the current measures and groupbys, so we can restore the view
         * when we save the current state in the search view, or when we add it to
         * the dashboard.
         *
         * @override method from AbstractController
         * @returns {Object}
         */
        getOwnedQueryParams: function () {
            const state = this.model.get({ raw: true });
            return {
                context: {
                    pivot_measures: state.measures,
                    pivot_column_groupby: state.colGroupBys,
                    pivot_row_groupby: state.rowGroupBys,
                }
            };
        },
        /**
         * Render the buttons according to the PivotView.buttons template and
         * add listeners on it.
         * Set this.$buttons with the produced jQuery element
         *
         * @override
         * @param {jQuery} [$node] a jQuery node where the rendered buttons should
         *   be inserted. $node may be undefined, in which case the PivotView
         *   does nothing
         */
        renderButtons: function ($node) {
            const context = this._getRenderButtonContext();
            this.$buttons = $(QWeb.render('PivotView.buttons', context));
            this.$buttons.click(this._onButtonClick.bind(this));
            this.$buttons.find('button').tooltip();
            if ($node) {
                this.$buttons.appendTo($node);
            }
        },
        /**
         * @override
         */
        updateButtons: function () {
            if (!this.$buttons) {
                return;
            }
            const state = this.model.get({ raw: true });
            Object.entries(this.measures).forEach(elt => {
                const name = elt[0];
                const isSelected = state.measures.includes(name);
                this.$buttons.find('.dropdown-item[data-field="' + name + '"]')
                    .toggleClass('selected', isSelected);

            });
            const noDataDisplayed = !state.hasData || !state.measures.length;
            this.$buttons.find('.o_pivot_flip_button').prop('disabled', noDataDisplayed);
            this.$buttons.find('.o_pivot_expand_button').prop('disabled', noDataDisplayed);
            this.$buttons.find('.o_pivot_download').prop('disabled', noDataDisplayed);
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Export the current pivot table data in a xls file. For this, we have to
         * serialize the current state, then call the server /web/pivot/export_xlsx.
         * Force a reload before exporting to ensure to export up-to-date data.
         *
         * @private
         */
        _downloadTable: function () {
            if (this.model.getTableWidth() > 16384) {
                this.call('crash_manager', 'show_message', _t("For Excel compatibility, data cannot be exported if there are more than 16384 columns.\n\nTip: try to flip axis, filter further or reduce the number of measures."));
                framework.unblockUI();
                return;
            }
            const table = this.model.exportData();
            table.title = this.title;
            table.model = this.modelName;
            session.get_file({
                url: '/web/pivot/export_xlsx',
                data: { data: JSON.stringify(table) },
                complete: framework.unblockUI,
                error: (error) => this.call('crash_manager', 'rpc_error', error),
            });
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * This handler is called when the user clicked on a button in the control
         * panel.  We then have to react properly: it can either be a change in the
         * current measures, or a request to flip/expand/download data.
         *
         * @private
         * @param {MouseEvent} ev
         */
        _onButtonClick: async function (ev) {
            const $target = $(ev.target);
            if ($target.hasClass('o_pivot_flip_button')) {
                this.model.flip();
                this.update({}, { reload: false });
            }
            if ($target.hasClass('o_pivot_expand_button')) {
                await this.model.expandAll();
                this.update({}, { reload: false });
            }
            if (ev.target.closest('.o_pivot_measures_list')) {
                ev.preventDefault();
                ev.stopPropagation();
                const field = ev.target.dataset.field;
                if (field) {
                    this.update({ measure: field });
                }
            }
            if ($target.hasClass('o_pivot_download')) {
                this._downloadTable();
            }

            await this._addIncludedButtons(ev);
        },

        /**
         * Declared to be overwritten in includes of pivot controller
         *
         * @param {MouseEvent} ev
         * @returns {Promise<void>}
         * @private
         */
        _addIncludedButtons: async function(ev) {},
        /**
         * Get the context of rendering of the buttons
         *
         * @returns {Object}
         * @private
         */
        _getRenderButtonContext: function () {
            return {
                measures: Object.entries(this.measures)
                .filter(x => x[0] !== '__count')
                .sort((a, b) => a[1].string.toLowerCase() > b[1].string.toLowerCase() ? 1 : -1),
            };
        },
        /**
         *
         * @private
         * @param {OdooEvent} ev
         */
        _onCloseGroup: function (ev) {
            this.model.closeGroup(ev.data.groupId, ev.data.type);
            this.update({}, { reload: false });
        },
        /**
         * @param {CustomEvent} ev
         * @private
         * */
        _onOpenedHeaderClicked: function (ev) {
            this.model.closeGroup(ev.data.cell.groupId, ev.data.type);
            this.update({}, { reload: false });
        },
        /**
         * @param {CustomEvent} ev
         * @private
         * */
        _onClosedHeaderClicked: async function (ev) {
            const cell = ev.data.cell;
            const groupId = cell.groupId;
            const type = ev.data.type;

            const group = {
                rowValues: groupId[0],
                colValues: groupId[1],
                type: type
            };

            const state = this.model.get({ raw: true });
            const groupValues = type === 'row' ? groupId[0] : groupId[1];
            const groupBys = type === 'row' ?
                state.rowGroupBys :
                state.colGroupBys;
            this.selectedGroup = group;
            if (groupValues.length < groupBys.length) {
                const groupBy = groupBys[groupValues.length];
                await this.model.expandGroup(this.selectedGroup, groupBy);
                this.update({}, { reload: false });
            }
        },
        /**
         * This handler is called when the user selects a groupby in the dropdown menu.
         *
         * @private
         * @param {CustomEvent} ev
         */
        _onGroupByMenuSelection: async function (ev) {
            ev.stopPropagation();

            const { fieldName, interval } = ev.data;
            let groupBy = fieldName;
            if (interval) {
                groupBy = `${groupBy}:${interval}`;
            }
            this.model.addGroupBy(groupBy, this.selectedGroup.type);
            await this.model.expandGroup(this.selectedGroup, groupBy);
            this.update({}, { reload: false });
        },
        /**
         * @private
         * @param {CustomEvent} ev
         */
        _onOpenView: function (ev) {
            ev.stopPropagation();
            const cell = ev.data;
            if (cell.value === undefined || this.disableLinking) {
                return;
            }

            const context = Object.assign({}, this.model.data.context);
            Object.keys(context).forEach(x => {
                if (x === 'group_by' || x.startsWith('search_default_')) {
                    delete context[x];
                }
            });

            const group = {
                rowValues: cell.groupId[0],
                colValues: cell.groupId[1],
                originIndex: cell.originIndexes[0]
            };

            const domain = this.model._getGroupDomain(group);

            this.do_action({
                type: 'ir.actions.act_window',
                name: this.title,
                res_model: this.modelName,
                views: this.views,
                view_mode: 'list',
                target: 'current',
                context: context,
                domain: domain,
            });
        },
        /**
         * @private
         * @param {CustomEvent} ev
         */
        _onSortRows: function (ev) {
            this.model.sortRows({
                groupId: ev.data.groupId,
                measure: ev.data.measure,
                order: (ev.data.order || 'desc') === 'asc' ? 'desc' : 'asc',
                originIndexes: ev.data.originIndexes,
            });
            this.update({}, { reload: false });
        },
    });

    export default PivotController;
