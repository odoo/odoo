odoo.define('account.payment', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var core = require('web.core');
var field_registry = require('web.field_registry');
var field_utils = require('web.field_utils');

var QWeb = core.qweb;
var _t = core._t;

var ShowPaymentLineWidget = AbstractField.extend({
    events: _.extend({
        'click .outstanding_credit_assign': '_onOutstandingCreditAssign',
        'click .open_account_move': '_onOpenPayment',
    }, AbstractField.prototype.events),
    supportedFieldTypes: ['char'],

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @returns {boolean}
     */
    isSet: function() {
        return true;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @override
     */
    _render: function() {
        this.viewAlreadyOpened = false;
        var self = this;
        var info = JSON.parse(this.value);
        if (!info) {
            this.$el.html('');
            return;
        }
        _.each(info.content, function (k, v){
            k.index = v;
            k.amount = field_utils.format.float(k.amount, {digits: k.digits});
            if (k.date){
                k.date = field_utils.format.date(field_utils.parse.date(k.date, {}, {isUTC: true}));
            }
        });
        this.$el.html(QWeb.render('ShowPaymentInfo', {
            lines: info.content,
            outstanding: info.outstanding,
            title: info.title
        }));
        _.each(this.$('.js_payment_info'), function (k, v){
            var isRTL = _t.database.parameters.direction === "rtl";
            var content = info.content[v];
            var options = {
                content: function () {
                    var $content = $(QWeb.render('PaymentPopOver', content));
                    var unreconcile_button = $content.filter('.js_unreconcile_payment').on('click', self._onRemoveMoveReconcile.bind(self));

                    $content.filter('.js_open_payment').on('click', self._onOpenPayment.bind(self));
                    return $content;
                },
                html: true,
                placement: isRTL ? 'bottom' : 'left',
                title: 'Payment Information',
                trigger: 'focus',
                delay: { "show": 0, "hide": 100 },
                container: $(k).parent(), // FIXME Ugly, should use the default body container but system & tests to adapt to properly destroy the popover
            };
            $(k).popover(options);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @override
     * @param {MouseEvent} event
     */
    _onOpenPayment: function (event) {
        var paymentId = parseInt($(event.target).attr('payment-id'));
        var moveId = parseInt($(event.target).attr('move-id'));
        var resModel;
        var id;
        if (paymentId !== undefined && !isNaN(paymentId)){
            resModel = "account.payment";
            id = paymentId;
        } else if (moveId !== undefined && !isNaN(moveId)){
            resModel = "account.move";
            id = moveId;
        }
        //Open form view of account.move with id = move_id
        //viewAlreadyopened is a flag to prevent the user from clicking on another account.move/account.payment
        //while the first one he clicked on is loading
        if (!this.viewAlreadyOpened && resModel && id) {
            this.viewAlreadyOpened = true;
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: resModel,
                res_id: id,
                views: [[false, 'form']],
                target: 'current'
            });
        }
    },
    /**
     * @private
     * @override
     * @param {MouseEvent} event
     */
    _onOutstandingCreditAssign: function (event) {
        event.stopPropagation();
        event.preventDefault();
        var self = this;
        var id = $(event.target).data('id') || false;
        this._rpc({
                model: 'account.move',
                method: 'js_assign_outstanding_line',
                args: [JSON.parse(this.value).move_id, id],
            }).then(function () {
                self.trigger_up('reload');
            });
    },
    /**
     * @private
     * @override
     * @param {MouseEvent} event
     */
    _onRemoveMoveReconcile: function (event) {
        var self = this;
        var moveId = parseInt($(event.target).attr('move-id'));
        var partialId = parseInt($(event.target).attr('partial-id'));
        if (partialId !== undefined && !isNaN(partialId)){
            this._rpc({
                model: 'account.move',
                method: 'js_remove_outstanding_partial',
                args: [moveId, partialId],
            }).then(function () {
                self.trigger_up('reload');
            });
        }
    },
});

field_registry.add('payment', ShowPaymentLineWidget);

return {
    ShowPaymentLineWidget: ShowPaymentLineWidget
};

});
