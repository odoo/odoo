odoo.define('sale_stock.QtyAtDateWidget', function (require) {
"use strict";

var core = require('web.core');
var QWeb = core.qweb;

var Widget = require('web.Widget');
var widget_registry = require('web.widget_registry');
var utils = require('web.utils');

var _t = core._t;
var time = require('web.time');

var QtyAtDateWidget = Widget.extend({
    template: 'sale_stock.qtyAtDate.Legacy',
    events: _.extend({}, Widget.prototype.events, {
        'click .fa-area-chart': '_onClickButton',
    }),

    /**
     * @override
     * @param {Widget|null} parent
     * @param {Object} params
     */
    init: function (parent, params) {
        this.data = params.data;
        this.fields = params.fields;
        this._updateData();
        this._super(parent);
    },

    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self._setPopOver();
        });
    },

    _updateData: function() {
        // add some data to simplify the template
        if (this.data.scheduled_date) {
            var qty_to_deliver = utils.round_decimals(this.data.qty_to_deliver, this.fields.qty_to_deliver.digits[1]);
            if (this.data.state === 'sale') {
                this.data.will_be_fulfilled = utils.round_decimals(this.data.free_qty_today, this.fields.free_qty_today.digits[1]) >= qty_to_deliver
            } else {
                this.data.will_be_fulfilled = utils.round_decimals(this.data.virtual_available_at_date, this.fields.virtual_available_at_date.digits[1]) >= qty_to_deliver
            }
            this.data.will_be_late = this.data.forecast_expected_date && this.data.forecast_expected_date > this.data.scheduled_date;
            if (['draft', 'sent'].includes(this.data.state)){
                // Moves aren't created yet, then the forecasted is only based on virtual_available of quant
                this.data.forecasted_issue = !this.data.will_be_fulfilled && !this.data.is_mto;
            } else {
                // Moves are created, using the forecasted data of related moves
                this.data.forecasted_issue = !this.data.will_be_fulfilled || this.data.will_be_late;
            }
        }
    },
    
    updateState: function (state) {
        this.$el.popover('dispose');
        var candidate = state.data[this.getParent().currentRow];
        if (candidate) {
            this.data = candidate.data;
            this._updateData();
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
        // TODO: in case of kit product, the forecast view should show the kit's components (get_component)
        // The forecast_report doesn't not allow for now multiple products 
        var action = await this._rpc({
            model: 'product.product',
            method: 'action_product_forecast_report',
            args: [[this.data.product_id.data.id]]
        });
        action.context = {
            active_model: 'product.product',
            active_id: this.data.product_id.data.id,
            warehouse: this.data.warehouse_id && this.data.warehouse_id.res_id,
            move_to_match_ids: this.data.move_ids.res_ids,
            sale_line_to_match_id: this.data.id,
        };
        return this.do_action(action);
    },

    _getContent() {
        if (!this.data.scheduled_date) {
            return;
        }
        this.data.delivery_date = this.data.scheduled_date.clone().add(this.getSession().getTZOffset(this.data.scheduled_date), 'minutes').format(time.getLangDateFormat());
        if (this.data.forecast_expected_date) {
            this.data.forecast_expected_date_str = this.data.forecast_expected_date.clone().add(this.getSession().getTZOffset(this.data.forecast_expected_date), 'minutes').format(time.getLangDateFormat());
        }
        const $content = $(QWeb.render('sale_stock.QtyDetailPopOver.Legacy', {
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
        this.$el.find('.fa-area-chart').prop('special_click', true);
    },
});

widget_registry.add('qty_at_date_widget', QtyAtDateWidget);

return QtyAtDateWidget;
});
