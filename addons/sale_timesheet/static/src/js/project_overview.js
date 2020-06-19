odoo.define('sale_timesheet.project_overview', function (require) {
    "use strict";

    var qweb = require('web.qweb');
    var viewRegistry = require('web.view_registry');

    const Controller = qweb.Controller.extend({
        events: _.extend({}, qweb.Controller.prototype.events, {
            'click .project_overview_foldable': '_onFoldToggle',
        }),

        _onFoldToggle(ev) {
            const {model, resId} = ev.target.dataset;
            const shouldOpen = ev.target.classList.contains('fa-caret-right');
            if (model === 'sale.order' && shouldOpen) {
                this._openSaleOrder(resId);
            }
            else if (model === 'sale.order.line' && shouldOpen) {
                this._openSaleOrderLine(resId);
            }
            else {
                const targetClass = `.${model.replace(/\./g, '_')}_${resId || 'None'}`;
                this.$(targetClass).hide();
            }
            $(ev.target).toggleClass('fa-caret-right');
            $(ev.target).toggleClass('fa-caret-down');
        },

        _openSaleOrder(id) {
            id = id || 'None';
            const targetClass = `.sale_order_${id}`;
            this.$(`.o_timesheet_forecast_sale_order_line${targetClass}`).show();
            this.$(`.o_timesheet_forecast_hr_employee${targetClass}`).hide();
            this.$(`.o_timesheet_forecast_sale_order_line${targetClass} .fa`).removeClass('fa-caret-down');
            this.$(`.o_timesheet_forecast_sale_order_line${targetClass} .fa`).addClass('fa-caret-right');

        },

        _openSaleOrderLine(id) {
            id = id || 'None';
            const targetClass = `.sale_order_line_${id}`;
            this.$(`.o_timesheet_forecast_hr_employee${targetClass}`).show();
        },
    });

    var ProjectOverview = qweb.View.extend({
        withSearchBar: true,
        searchMenuTypes: ['filter', 'favorite'],

        config: _.extend({}, qweb.View.prototype.config, {
            Controller: Controller,
        }),
    });

    viewRegistry.add('project_overview', ProjectOverview);
});
