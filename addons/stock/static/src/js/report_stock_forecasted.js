odoo.define('stock.ReplenishReport', function (require) {
"use strict";

const clientAction = require('report.client_action');
const core = require('web.core');
const dom = require('web.dom');
const GraphRenderer = require("web/static/src/js/views/graph/graph_renderer");
const GraphView = require('web.GraphView');

const qweb = core.qweb;
const _t = core._t;

class StockReportGraphRenderer extends GraphRenderer {}

StockReportGraphRenderer.template = "stock.GraphRenderer";

const StockReportGraphView = GraphView.extend({
    config: Object.assign({}, GraphView.prototype.config, {
        Renderer: StockReportGraphRenderer,
    }),
});

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
        this.iframe.addEventListener("load",
            () => this._bindAdditionalActionHandlers(),
            { once: true }
        );
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Promise<GraphController>} graphPromise
     * @returns {Promise}
     */
    async _appendGraph(graphPromise) {
        const graphController = await graphPromise;
        const iframeDoc = this.iframe.contentDocument;
        const reportGraphDiv = iframeDoc.querySelector(".o_report_graph");
        dom.append(reportGraphDiv, graphController.el, {
            in_DOM: true,
            callbacks: [{ widget: graphController }],
        });
        // Hack to put the res_model on the url. This way, the report always know on with res_model it refers.
        if (location.href.indexOf('active_model') === -1) {
            const url = window.location.href + `&active_model=${this.resModel}`;
            window.history.pushState({}, "", url);
        }
    },

    /**
     * @private
     * @returns {Promise<GraphController>}
     */
    async _createGraphController() {
        const model = "report.stock.quantity";
        const viewInfo = await this._rpc({
            model,
            method: "fields_view_get",
            kwargs: { view_type: "graph" }
        });
        const params = {
            domain: this._getReportDomain(),
            modelName: model,
            noContentHelp: _t("Try to add some incoming or outgoing transfers."),
            withControlPanel: false,
        };
        const graphView = new StockReportGraphView(viewInfo, params);
        const graphController = await graphView.getController(this);
        await graphController.appendTo(document.createDocumentFragment());
        return graphController;
    },

    /**
     * Instantiates a chart graph and moves it into the report's iframe.
     */
    _createGraphView() {
        const graphPromise = this._createGraphController();
        this.iframe.addEventListener("load",
            () => this._appendGraph(graphPromise),
            { once: true }
        );
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

    /**
     * Bind additional action handlers (<button>, <a>)
     * 
     * @returns {Promise}
     */
    _bindAdditionalActionHandlers: function () {
        let rr = this.$el.find('iframe').contents().find('.o_report_replenishment');
        rr.on('click', '.o_report_replenish_change_priority', this._onClickChangePriority.bind(this));
        rr.on('mouseenter', '.o_report_replenish_change_priority', this._onMouseEnterPriority.bind(this));
        rr.on('mouseleave', '.o_report_replenish_change_priority', this._onMouseLeavePriority.bind(this));
        rr.on('click', '.o_report_replenish_unreserve', this._onClickUnreserve.bind(this));
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
    },

    /**
     * Change the priority of the specified model/id, then reload this report.
     *
     * @returns {Promise}
     */
    _onClickChangePriority: function(ev) {
        const model = ev.target.getAttribute('model');
        const modelId = parseInt(ev.target.getAttribute('model-id'));
        const value = ev.target.classList.contains('zero')?'1':'0';
        this._rpc( {
            model: model,
            args: [[modelId], {priority: value}],
            method: 'write'
        }).then((result) => {
            return this._reloadReport();
        });
    },
    _onMouseEnterPriority: function(ev) {
        ev.target.classList.toggle('fa-star');
        ev.target.classList.toggle('fa-star-o');
    },
    _onMouseLeavePriority: function(ev) {
        ev.target.classList.toggle('fa-star');
        ev.target.classList.toggle('fa-star-o');
    },

    /**
     * Unreserve the specified model/id, then reload this report.
     *
     * @returns {Promise}
     */
    _onClickUnreserve: function(ev) {
        const model = ev.target.getAttribute('model');
        const modelId = parseInt(ev.target.getAttribute('model-id'));
        this._rpc( {
            model: model,
            args: [[modelId]],
            method: 'do_unreserve'
        }).then((result) => {
            return this._reloadReport();
        });
    }

});

core.action_registry.add('replenish_report', ReplenishReport);

return(ReplenishReport);

});
