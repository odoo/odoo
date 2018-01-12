odoo.define('stock.ReportWidget', function (require) {
'use strict';

var core = require('web.core');
var Widget = require('web.Widget');

var QWeb = core.qweb;

var _t = core._t;

var ReportWidget = Widget.extend({
    events: {
        'click span.o_stock_reports_foldable': 'fold',
        'click span.o_stock_reports_unfoldable': 'unfold',
        'click .o_stock_reports_web_action': 'boundLink',
        'click .o_stock_reports_stream': 'updownStream',
    },
    init: function(parent) {
        this._super.apply(this, arguments);
    },
    start: function() {
        QWeb.add_template("/stock/static/src/xml/stock_traceability_report_line.xml");
        return this._super.apply(this, arguments);
    },
    boundLink: function(e) {
        return this.do_action({
            type: 'ir.actions.act_window',
            res_model: $(e.target).data('res-model'),
            res_id: $(e.target).data('active-id'),
            views: [[false, 'form']],
            target: 'current'
        });
    },
    updownStream: function(e) {
        var $el = $(e.target).parents('tr');
        var string = "Traceability Report";
        console.log($el.data('lot_id'));
        this.do_action({
            type: "ir.actions.client",
            tag: 'stock_report_generic',
            name: _t(string),
            context: {
                active_id : $el.data('model_id'),
                active_model : $el.data('model'),
                auto_unfold: true,
                lot_id: $el.data('lot_id') !== undefined && $el.data('lot_id').toString(),
                url: '/stock/output_format/stock/active_id'
            },
        });
    },
    removeLine: function(element) {
        var self = this;
        var el, $el;
        var rec_id = element.data('id');
        var $stockEl = element.nextAll('tr[data-parent_id=' + rec_id + ']')
        for (el in $stockEl) {
            $el = $($stockEl[el]).find(".o_stock_reports_domain_line_0, .o_stock_reports_domain_line_1");
            if ($el.length === 0) {
                break;
            }
            else {
                var $nextEls = $($el[0]).parents("tr");
                self.removeLine($nextEls);
                $nextEls.remove();
            }
            $el.remove();
        }
        return true;
    },
    fold: function(e) {
        this.removeLine($(e.target).parents('tr'));
        var active_id = $(e.target).parents('tr').find('td.o_stock_reports_foldable').data('id');
        $(e.target).parents('tr').find('td.o_stock_reports_foldable').attr('class', 'o_stock_reports_unfoldable ' + active_id); // Change the class, rendering, and remove line from model
        $(e.target).parents('tr').find('span.o_stock_reports_foldable').replaceWith(QWeb.render("unfoldable", {lineId: active_id}));
        $(e.target).parents('tr').toggleClass('o_stock_reports_unfolded');
    },
    autounfold: function(target, lot_id) {
        var self = this;
        var $CurretElement;
        $CurretElement = $(target).parents('tr').find('td.o_stock_reports_unfoldable');
        var active_id = $CurretElement.data('id');
        var active_model_name = $CurretElement.data('model');
        var active_model_id = $CurretElement.data('model_id');
        var row_level = $CurretElement.data('level');
        var $cursor = $(target).parents('tr');
        this._rpc({
                model: 'stock.traceability.report',
                method: 'get_lines',
                args: [parseInt(active_id, 10)],
                kwargs: {
                    'model_id': active_model_id,
                    'model_name': active_model_name,
                    'level': parseInt(row_level) + 30 || 1
                },
            })
            .then(function (lines) {// After loading the line
                _.each(lines, function (line) { // Render each line
                    $cursor.after(QWeb.render("report_mrp_line", {l: line}));
                    $cursor = $cursor.next();
                    if ($cursor && line.unfoldable && line.lot_id == lot_id) {
                        self.autounfold($cursor.find(".fa-caret-right"), lot_id);
                    }
                });
            });
        $CurretElement.attr('class', 'o_stock_reports_foldable ' + active_id); // Change the class, and rendering of the unfolded line
        $(target).parents('tr').find('span.o_stock_reports_unfoldable').replaceWith(QWeb.render("foldable", {lineId: active_id}));
        $(target).parents('tr').toggleClass('o_stock_reports_unfolded');
    },
    unfold: function(e) {
        this.autounfold($(e.target));
    },

});

return ReportWidget;

});
