odoo.define('stock.ReplenishReport', function (require) {
"use strict";

const { loadLegacyViews } = require("@web/legacy/legacy_views");

const clientAction = require('report.client_action');
const core = require('web.core');
const dom = require('web.dom');

const qweb = core.qweb;
const _t = core._t;

const viewRegistry = require("web.view_registry");

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
        this._title = action.name;
    },

    /**
     * @override
     */
    willStart: function() {
        var loadWarehouses = this._rpc({
            model: 'report.stock.report_product_product_replenishment',
            method: 'get_warehouses',
            context: this.context,
        }).then((res) => {
            this.warehouses = res;
            if (this.context.warehouse) {
                this.active_warehouse = this.warehouses.find(w => w.id == this.context.warehouse);
            }
            else {
                this.active_warehouse = this.warehouses[0];
                this.context.warehouse = this.active_warehouse.id;
            }
            this.report_url += `?context=${JSON.stringify(this.context)}`;
        });
        return Promise.all([
            this._super.apply(this, arguments),
            loadWarehouses,
            loadLegacyViews({ rpc: this._rpc.bind(this) }),
        ]);
    },

    /**
     * @override
     */
    start: function () {
        return Promise.all([
            this._super(...arguments),
        ]).then(() => {
            this._renderWarehouseFilters();
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
        if (!reportGraphDiv) {
            return;
        }
        dom.append(reportGraphDiv, graphController.el, {
            in_DOM: true,
            callbacks: [{ widget: graphController }],
        });
        // Hack to put the res_model on the url. This way, the report always know on with res_model it refers.
        if (location.href.indexOf('active_model') === -1) {
            const url = window.location.href + `&active_model=${this.resModel}`;
            window.history.replaceState({}, "", url);
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
            context: {fill_temporal: false},
        };
        const GraphView = viewRegistry.get("graph");
        const graphView = new GraphView(viewInfo, params);
        const graphController = await graphView.getController(this);
        await graphController.appendTo(document.createDocumentFragment());

        // Since we render the container in a fragment, we may endup in this case:
        // https://github.com/chartjs/Chart.js/issues/2210#issuecomment-204984449
        // so, the canvas won't be resizing when it is relocated in the iframe.
        // Also, since the iframe's position is absolute, chartJS reiszing may not work
        //  (https://www.chartjs.org/docs/2.9.4/general/responsive.html -- #Important Note)
        // Finally, we do want to set a height for the canvas rendering in chartJS.
        // We do this via the chartJS API, that is legacy/graph_renderer.js:@_prepareOptions
        //  (maintainAspectRatio = false) and with the *attribute* height (not the style).
        //  (https://www.chartjs.org/docs/2.9.4/general/responsive.html -- #Responsive Charts)
        // Luckily, the chartJS is not fully rendered, so changing the height here is relevant.
        // It wouldn't be if we were after GraphRenderer@mounted.
        graphController.el.querySelector(".o_graph_canvas_container canvas").height = "300";

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
            return this.do_action(action, { stackPosition: 'replaceCurrentAction' });
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
     * Renders the Warehouses filter
     */
    _renderWarehouseFilters: function () {
        const $filters = $(qweb.render('warehouseFilter', {
            active_warehouse: this.active_warehouse,
            warehouses: this.warehouses,
            displayWarehouseFilter: (this.warehouses.length > 1),
        }));
        // Bind handlers.
        $filters.on('click', '.warehouse_filter', this._onClickFilter.bind(this));
        this.$('.o_search_options').append($filters);
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
        rr.on('click', '.o_report_replenish_reserve', this._onClickReserve.bind(this));
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
        return this._rpc( {
            model,
            args: [[modelId]],
            method: 'do_unreserve'
        }).then(() => this._reloadReport());
    },

    /**
     * Reserve the specified model/id, then reload this report.
     *
     * @returns {Promise}
     */
    _onClickReserve: function(ev) {
        const model = ev.target.getAttribute('model');
        const modelId = parseInt(ev.target.getAttribute('model-id'));
        return this._rpc( {
            model,
            args: [[modelId]],
            method: 'action_assign'
        }).then(() => this._reloadReport());
    }

});

core.action_registry.add('replenish_report', ReplenishReport);

return(ReplenishReport);

});
