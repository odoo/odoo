odoo.define('mrp.mrp_bom_generic', function (require) {
'use strict';

var ControlPanelMixin = require('web.ControlPanelMixin');
var core = require('web.core');
var crash_manager = require('web.crash_manager');
var framework = require('web.framework');
var session = require('web.session');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

var mrpBomReport = Widget.extend(ControlPanelMixin, {
    events: {
        'click span.o_mrp_bom_unfoldable': '_onUnfold',
        'click span.o_mrp_bom_foldable': '_onFold',
        'click a.o_mrp_reports_web_action' : '_onBoundLink',
    },

    /**
     * @override
     */
    init: function (parent, action) {
        this.actionManager = parent;
        this.given_context = action.context.context || {'active_id': action.context.active_id || action.params.active_id};
        this.button = {'name': _t('Print')};
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    willStart: function () {
        return this._getMrpBomHtml();
    },
    /**
     * @override
     */
    start: function () {
        this.$el.html(this.html);
        return this._super();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    do_show: function () {
        this._super();
        this.update_cp();
    },
    update_cp: function () {
        // Updates the control panel and render the elements that have yet to be rendered
        if (!this.$button) {
            this.renderButton();
        }
        var status = {
            breadcrumbs: this.actionManager.get_breadcrumbs(),
            cp_content: {$buttons: this.$button},
        };
        return this.update_control_panel(status);
    },
    renderButton: function () {
        var self = this;
        this.$button = $(QWeb.render("mrp.button", {button: this.button}));
        // bind actions
        $(this.$button).click(function () {
            var child_bom_ids = _.map(self.$el.find('.o_mrp_bom_foldable').closest('tr'), function (ele) {
                    return $(ele).data('id');
                });
            var bom_id = self.given_context['active_id'];
            framework.blockUI();
            session.get_file({
                url: '/mrp/pdf/bom_report/'+bom_id,
                data: {child_bom_ids: JSON.stringify(child_bom_ids)},
                complete: framework.unblockUI,
                error: crash_manager.rpc_error.bind(crash_manager),
            });
        });
        return this.$button;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Fetches the html and is previous report.context if any, else create it
     *
     * @private
     */
    _getMrpBomHtml: function () {
        var self = this;
        var cpDef = this.update_cp();
        var rpcDef  = this._rpc({
                model: 'mrp.bom.report',
                method: 'get_html',
                args: [self.given_context],
            })
            .then(function (result) {
                self.html = result;
            });
        return $.when(cpDef, rpcDef);
    },
    /**
     * Remove child lines
     *
     * @private
     * @param {Object} el
     */
    _removeLines: function (el) {
        var activeId = el.data('id');
        var $parent = $('tr[parent_id='+ activeId +']');

        for (var i = 0; i < $parent.length; i++) {
            var $el = $('tr[parent_id='+ $($parent[i]).data('id') +']');
            if ($el.length) {
                this._removeLines($($parent[i]));
            }
            $parent[i].remove();
        }
        return true;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Display child lines
     *
     * @private
     * @param {MouseEvent} ev
     */
     _onUnfold: function (ev) {
        var self = this;
        var $parent = $(ev.target).closest('tr');
        var activeId = $parent.data('id');
        var qty = $parent.data('qty');
        var level = $parent.data('level') || 0;

        this._rpc({
                model: 'mrp.bom.report',
                method: 'get_html',
                args: [self.given_context, activeId, parseFloat(qty), level+1],
            })
            .then(function (data) {
                $parent.after(data);
            });
        $(ev.target).toggleClass('o_mrp_bom_foldable o_mrp_bom_unfoldable fa-caret-right fa-caret-down');
    },
    /**
     * Hide child lines
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onFold: function (ev) {
        this._removeLines($(ev.target).closest('tr'));
        $(ev.target).toggleClass('o_mrp_bom_foldable o_mrp_bom_unfoldable fa-caret-right fa-caret-down');
    },
    /**
     * Redirect to the product page
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onBoundLink: function (ev) {
        return this.do_action({
            type: 'ir.actions.act_window',
            res_model: $(ev.target).data('model'),
            res_id: $(ev.target).data('res-id'),
            views: [[false, 'form']],
            target: 'current'
        });
    },
});

core.action_registry.add("mrp_bom_report", mrpBomReport);
return mrpBomReport;
});
