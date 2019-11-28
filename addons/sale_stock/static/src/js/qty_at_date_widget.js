odoo.define('sale_stock.QtyAtDateWidget', function (require) {
"use strict";

var core = require('web.core');
var QWeb = core.qweb;

var Widget = require('web.Widget');
var Context = require('web.Context');
var data_manager = require('web.data_manager');
var widget_registry = require('web.widget_registry');
var config = require('web.config');

var _t = core._t;
var time = require('web.time');

var QtyAtDateWidget = Widget.extend({
    template: 'sale_stock.qtyAtDate',
    events: _.extend({}, Widget.prototype.events, {
        'click .fa-info-circle': '_onClickButton',
    }),

    /**
     * @override
     * @param {Widget|null} parent
     * @param {Object} params
     */
    init: function (parent, params) {
        this.data = params.data;
        this._super(parent);
    },

    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self._setPopOver();
        });
    },

    updateState: function (state) {
        this.$el.popover('dispose');
        var candidate = state.data[this.getParent().currentRow];
        if (candidate) {
            this.data = candidate.data;
            this.renderElement();
            this._setPopOver();
        }
    },
    /**
     * Redirect to the product graph view.
     *
     * @private
     * @param {MouseEvent} event
     * @returns {Promise} action loaded
     */
    async _openForecast(ev) {
        ev.stopPropagation();
        // Change action context to choose a specific date and product(s)
        // As grid_anchor is set to now() by default in the data, we need
        // to load the action first, change the context then launch it via do_action
        // additional_context cannot replace a context value, only add new
        //
        // in case of kit product, the forecast view show the kit's components
        const [action, res] = await Promise.all([
            data_manager.load_action('stock.report_stock_quantity_action_product'),
            this._rpc({
                model: 'product.product',
                method: 'get_components',
                args: [[this.data.product_id.data.id]]
            })
        ]);
        const additional_context = {
            grid_anchor: this.data.delivery_date_grid,
            search_default_warehouse_id: [this.data.warehouse_id.data.id],
            search_default_below_warehouse: false
        };
        action.context = new Context(action.context, additional_context);
        action.domain = [
            ['product_id', 'in', res]
        ];
        return this.do_action(action);
    },

    _getContent() {
        if (!this.data.scheduled_date) {
            return;
        }
        this.data.delivery_date = this.data.scheduled_date.clone().add(this.getSession().getTZOffset(this.data.scheduled_date), 'minutes').format(time.getLangDateFormat());
        // The grid view need a specific date format that could be different than
        // the user one.
        this.data.delivery_date_grid = this.data.scheduled_date.clone().add(this.getSession().getTZOffset(this.data.scheduled_date), 'minutes').format('YYYY-MM-DD');
        this.data.debug = config.isDebug();
        const $content = $(QWeb.render('sale_stock.QtyDetailPopOver', {
            data: this.data,
        }));
        $content.on('click', '.action_open_forecast', this._openForecast.bind(this));
        return $content;
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    /**
     * Set a bootstrap popover on the current QtyAtDate widget that display available
     * quantity.
     */
    _setPopOver() {
        const $content = this._getContent();
        if (!$content) {
            return;
        }
        const options = {
            content: $content,
            html: true,
            placement: 'left',
            title: _t('Availability'),
            trigger: 'focus',
            delay: {'show': 0, 'hide': 100 },
        };
        this.$el.popover(options);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------
    _onClickButton: function () {
        // We add the property special click on the widget link.
        // This hack allows us to trigger the popover (see _setPopOver) without
        // triggering the _onRowClicked that opens the order line form view.
        this.$el.find('.fa-info-circle').prop('special_click', true);
    },
});

widget_registry.add('qty_at_date_widget', QtyAtDateWidget);

return QtyAtDateWidget;
});
