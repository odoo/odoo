odoo.define('report.bom_cost_structure', function (require) {
'use strict';
var core = require('web.core');
var ReportAction = core.action_registry.get('report.client_action');


var BomReportAction = ReportAction.extend({
    init: function (parent, action, options){
        var option = _.extend({}, options, {
                report_url: '/report/html/' + action.report_name + '/' + action.context.active_id,
                report_name: action.report_name,
                report_file: action.report_file,
                data: action.data,
                context: action.context,
                name: action.name,
                display_name: action.display_name,
            });
        this._super(parent, action, option);
    },
    openM2ORecord: function (ev){
        ev.stopPropagation();
        var action = {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'current',
            'res_id': Number($(this).attr('res-id')),
            'res_model': $(this).attr('res-model'),
            'views': [[false, 'form']],
        };
        window.parent.postMessage({
            'message': 'report:do_action',
            'action': action,
        }, window.location.origin);
    },
    _make_table_expandable: function ($body) {
        $body.find('.reports_m2o_web_action').on('click', this.openM2ORecord);
        $body.find('.header').hide();  // hide header
        var $trExpandable = $body.find('.tr_expandable');

        $trExpandable.on('click', function (ev, collapse){
            var id = $(this).data('id');
            var $caret =  $(this).find('.td-caret');
            var $table = $(this).closest('table');
            var downDirection =  $caret.hasClass('fa-caret-down') ? false : true;
            if (downDirection && !collapse) {
                $table.find("tr[data-parent-id="+ id +"]").removeClass('hidden');
                $caret.removeClass('fa-caret-right').addClass('fa-caret-down');
            } else {
                $table.find("tr[data-parent-id="+ id +"]").addClass('hidden');
                $table.find("tr[data-parent-id="+ id +"].tr_expandable").trigger('click', true);
                $caret.removeClass('fa-caret-down').addClass('fa-caret-right');
            }
        });
    },
    _add_variant_selector: function ($body) {
        var $product_select = $body.find('#product_select');
        if ($product_select.length){
            $body.find('div.page:not(:first)').addClass('hidden');
        }
        $product_select.on('change', function (ev){
            $body.find('.page').addClass('hidden');
            var variantID = $(this).val();
            var className = 'variant_' + variantID;
            $body.find('.' + className).removeClass('hidden');
        });
    },
    _on_iframe_loaded: function () {
        this._super.apply(this, arguments);
        var $body = $(this.iframe).contents().find('html body');
        this._make_table_expandable($body);
        this._add_variant_selector($body);
    },
});

core.action_registry.add('mrp_bom_cost_structure_report', BomReportAction);
return BomReportAction;
});
