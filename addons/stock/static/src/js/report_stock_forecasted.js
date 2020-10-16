odoo.define('stock.ReplenishReport', function (require) {
"use strict";

const clientAction = require('report.client_action');
const core = require('web.core');
const dom = require('web.dom');
const GraphView = require('web.GraphView');

const qweb = core.qweb;
const _t = core._t;


const ReplenishReport = clientAction.extend({
    /**
     * @override
     */
    init: function (parent, action, options) {
        this._super.apply(this, arguments);
        this.context = action.context;
        this.productId = this.context.active_id;
        this.resModel = this.context.active_model || this.context.params.active_model || 'product.template';
        const isTemplate = this.resModel === 'product.template';
        this.actionMethod = `action_product_${isTemplate ? 'tmpl_' : ''}forecast_report`;
        const reportName = `report_product_${isTemplate ? 'template' : 'product'}_replenishment`;
        this.report_url = `/report/html/stock.${reportName}/${this.productId}`;
        if (this.context.warehouse) {
            this.active_warehouse = {id: this.context.warehouse};
        }
        this.report_url += `?context=${JSON.stringify(this.context)}`;
        this._title = action.name;
    },

    /**
     * @override
     */
    start: function () {
        return Promise.all([
            this._super(...arguments),
            this._renderWarehouseFilters(),
        ]).then(() => {
            this._renderButtons();
        });
    },

    /**
     * @override
     */
    on_attach_callback: function () {
        this._super();
        this._createGraphView();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Instanciates a chart graph and moves it into the report (which is in the iframe).
     */
    _createGraphView: async function () {
        let viewController;
        const appendGraph = () => {
            promController.then(() => {
                this.iframe.removeEventListener('load', appendGraph);
                const $reportGraphDiv = $(this.iframe).contents().find('.o_report_graph');
                dom.append(this.$el, viewController.$el, {
                    in_DOM: true,
                    callbacks: [{widget: viewController}],
                });
                const renderer = viewController.renderer;
                // Remove the graph control panel.
                $('.o_control_panel:last').remove();
                const $graphPanel = $('.o_graph_controller');
                $graphPanel.appendTo($reportGraphDiv);

                if (!renderer.state.dataPoints.length) {
                    // Changes the "No Data" helper message.
                    const graphHelper = renderer.$('.o_view_nocontent');
                    const newMessage = qweb.render('View.NoContentHelper', {
                        description: _t("Try to add some incoming or outgoing transfers."),
                    });
                    graphHelper.replaceWith(newMessage);
                } else {
                    this.chart = renderer.chart;
                    // Lame hack to fix the size of the graph.
                    setTimeout(() => {
                        this.chart.canvas.height = 300;
                        this.chart.canvas.style.height = "300px";
                        this.chart.resize();
                    }, 1);
                }
            });
        };
        // Wait the iframe fo append the graph chart and move it into the iframe.
        this.iframe.addEventListener('load', appendGraph);

        const model = 'report.stock.quantity';
        const promController = this._rpc({
            model: model,
            method: 'fields_view_get',
            kwargs: {
                view_type: 'graph',
            }
        }).then(viewInfo => {
            const params = {
                modelName: model,
                domain: this._getReportDomain(),
                hasActionMenus: false,
            };
            const graphView = new GraphView(viewInfo, params);
            return graphView.getController(this);
        }).then(res => {
            viewController = res;

            // Hack to put the res_model on the url. This way, the report always know on with res_model it refers.
            if (location.href.indexOf('active_model') === -1) {
                const url = window.location.href + `&active_model=${this.resModel}`;
                window.history.pushState({}, "", url);
            }
            const fragment = document.createDocumentFragment();
            return viewController.appendTo(fragment);
        });
    },

    /**
     * Return the action to open this report.
     *
     * @returns {Promise}
     */
    _getForecastedReportAction: function () {
        return this._rpc({
            model: this.resModel,
            method: this.actionMethod,
            args: [this.productId],
            context: this.context,
        });
    },

    /**
     * Returns a domain to filter on the product variant or product template
     * depending of the active model.
     *
     * @returns {Array}
     */
    _getReportDomain: function () {
        const domain = [
            ['state', '=', 'forecast'],
            ['warehouse_id', '=', this.active_warehouse.id],
        ];
        if (this.resModel === 'product.template') {
            domain.push(['product_tmpl_id', '=', this.productId]);
        } else if (this.resModel === 'product.product') {
            domain.push(['product_id', '=', this.productId]);
        }
        return domain;
    },

    /**
     * TODO
     *
     * @param {Object} additionnalContext
     */
    _reloadReport: function (additionnalContext) {
        return this._getForecastedReportAction().then((action) => {
            action.context = Object.assign({
                active_id: this.productId,
                active_model: this.resModel,
            }, this.context, additionnalContext);
            return this.do_action(action, {replace_last_action: true});
        });
    },

    /**
     * Renders the 'Replenish' button and replaces the default 'Print' button by this new one.
     */
    _renderButtons: function () {
        const $newButtons = $(qweb.render('replenish_report_buttons', {}));
        this.$buttons.find('.o_report_print').replaceWith($newButtons);
        this.$buttons.on('click', '.o_report_replenish_buy', this._onClickReplenish.bind(this));
        this.controlPanelProps.cp_content = {
            $buttons: this.$buttons,
        };
    },

    /**
     * TODO
     * @returns {Promise}
     */
    _renderWarehouseFilters: function () {
        return this._rpc({
            model: 'report.stock.report_product_product_replenishment',
            method: 'get_filter_state',
        }).then((res) => {
            const warehouses = res.warehouses;
            const active_warehouse = (this.active_warehouse && this.active_warehouse.id) || res.active_warehouse;
            if (active_warehouse) {
                this.active_warehouse = _.findWhere(warehouses, {id: active_warehouse});
            } else {
                this.active_warehouse = warehouses[0];
            }
            const $filters = $(qweb.render('warehouseFilter', {
                active_warehouse: this.active_warehouse,
                warehouses: warehouses,
                displayWarehouseFilter: (warehouses.length > 1),
            }));
            // Bind handlers.
            $filters.on('click', '.warehouse_filter', this._onClickFilter.bind(this));
            this.$('.o_search_options').append($filters);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Opens the product replenish wizard. Could re-open the report if pending
     * forecasted quantities need to be updated.
     *
     * @returns {Promise}
     */
    _onClickReplenish: function () {
        const context = Object.assign({}, this.context);
        if (this.resModel === 'product.product') {
            context.default_product_id = this.productId;
        } else if (this.resModel === 'product.template') {
            context.default_product_tmpl_id = this.productId;
        }
        context.default_warehouse_id = this.active_warehouse.id;

        const on_close = function (res) {
            if (res && res.special) {
                // Do nothing when the wizard is discarded.
                return;
            }
            // Otherwise, opens again the report.
            return this._reloadReport();
        };

        const action = {
            res_model: 'product.replenish',
            name: _t('Product Replenish'),
            type: 'ir.actions.act_window',
            views: [[false, 'form']],
            target: 'new',
            context: context,
        };

        return this.do_action(action, {
            on_close: on_close.bind(this),
        });
    },

    /**
     * Re-opens the report with data for the specified warehouse.
     *
     * @returns {Promise}
     */
    _onClickFilter: function (ev) {
        const data = ev.target.dataset;
        const warehouse_id = Number(data.warehouseId);
        return this._reloadReport({warehouse: warehouse_id});
    }
});

core.action_registry.add('replenish_report', ReplenishReport);

});