odoo.define("pos_ipaymu.pos_ipaymu", function(require) {
    "use strict";

    var rpc = require("web.rpc");
    var screens = require("point_of_sale.screens");
    var pos_model = require("point_of_sale.models");
    var Dialog = require("web.Dialog");
    var core = require("web.core");
    var check_status;
    var PaymentScreenWidget = screens.PaymentScreenWidget;
    var core = require('web.core');
    var _t = core._t;
    var round_pr = require('web.utils').round_precision;

    var QWeb = core.qweb;
    var _t = core._t;

    pos_model.load_fields("account.journal", "pos_ipaymu_config_id");
    pos_model.load_fields("pos_ipaymu.configuration", "merchant_api_key");

    /** Payment Line
     * @include
     *
     * !!! same as pos_iot !!!
     */
    var _pl_proto = pos_model.Paymentline.prototype;
    pos_model.Paymentline = pos_model.Paymentline.extend({

        init_from_JSON: function(json) {
            _pl_proto.init_from_JSON.apply(this, arguments);
            if (json.payment_status) {
                if (['done', 'pending'].includes(json.payment_status)) {
                    this.payment_status = json.payment_status;
                } else {
                    this.payment_status = 'retry';
                }
            } else {
                this.payment_status = false;
            }
        },

        export_as_JSON: function() {
            var result = _pl_proto.export_as_JSON.apply(this, arguments);
            result.payment_status = this.payment_status || false;
            return result;
        },

        /**
         * returns {string} payment status.
         */
        get_payment_status: function() {
            return this.payment_status;
        },

        /**
         * Set the new payment status .
         *
         * @param {string} value - new status.
         */
        set_payment_status: function(value) {
            this.payment_status = value;
        },
    });

    /** PoS Order
     * @include
     *
     * !!! same as pos_iot !!!
     */
    pos_model.Order = pos_model.Order.extend({
        /**
         * @override
         * Only account the payment lines with status `done` to check if the order is fully payd.
         */
        get_total_paid: function() {
            return round_pr(this.paymentlines.reduce((function(sum, paymentLine) {
                if (paymentLine.get_payment_status()) {
                    if (['done'].includes(paymentLine.get_payment_status())) {
                        sum += paymentLine.get_amount();
                    }
                } else {
                    sum += paymentLine.get_amount();
                }
                return sum;
            }), 0), this.pos.currency.rounding);
        },
    });

    var _pm_proto = pos_model.PosModel.prototype;
    pos_model.PosModel = pos_model.PosModel.extend({

        render_html_for_customer_facing_display: function () {
            var bc = this.get_order().QrCode
            if (bc) {
                var self = this;
                return _pm_proto.render_html_for_customer_facing_display.call(this, {
                    'rendered_order_lines': QWeb.render('CustomerFacingDisplayQrCode', {
                        'QrCode': this.get_order().QrCode
                    })
                });
            }
            return _pm_proto.render_html_for_customer_facing_display.call(this);
        },

        getOnlinePaymentJournals: function() {
            var self = this;
            var online_payment_journals = [];

            $.each(this.journals, function(i, val) {
                if (val.pos_ipaymu_config_id) {
                    online_payment_journals.push({
                        label: self.getCashRegisterByJournalID(val.id).journal_id[1],
                        item: val.id
                    });
                }
            });

            return online_payment_journals;
        },
        getCashRegisterByJournalID: function(journal_id) {
            var cashregister_return;

            $.each(this.cashregisters, function(index, cashregister) {
                if (cashregister.journal_id[0] === journal_id) {
                    cashregister_return = cashregister;
                }
            });

            return cashregister_return;
        }
    });

    // On Payment screen, allow electronic payments
    PaymentScreenWidget.include({
        // How long we wait for the odoo server to deliver the response of
        // a IPaymu transaction
        server_timeout: 95000,

        start: function()
        {
            var order_id = this.pos.get_order();

            if(!order_id == null)
            {
                var line_ids = this.pos.get_order().get_paymentlines();
                this.pos.get_order().remove_paymentline(line_ids);
                this.reset_input();
                this.render_paymentlines();
            }
        },

        _get_ipaymu_pending_line: function() {
            var i = 0;
            var lines = this.pos.get_order().get_paymentlines();

            for (i = 0; i < lines.length; i++) {
                if (lines[i].ipaymu_pending) {
                    return lines[i];
                }
            }

            return 0;
        },
        click_delete_paymentline: function(id)
        {
            var line = this.pos.get_order().paymentlines._byId[id];
            if (line && line.cashregister.journal.pos_ipaymu_config_id) {
                this.set_ipaymu_status(line, 'cancel', true);
            }
            this._super(id);
        },

        /**
         * @override
         * link the proper functions to buttons for payment terminals
         * send_payment_request, Force_payment_done and cancel_payment.
         */
        render_paymentlines: function() {
            var self = this;
            this._super();
            var order = this.pos.get_order();
            if (!order) {
                return;
            }
            var line = order.selected_paymentline;
            if (line && line.cashregister.journal.pos_ipaymu_config_id) {
                this.$el.find('.send_payment_request').click(function () {
                    self.send_ipaymu_request(line);
                    self.set_ipaymu_status(line, 'waiting', false);
                    line.payment_timer = setTimeout ( function () {
                        self.set_ipaymu_status(line, 'retry', true);
                    }, self.server_timeout);
                });
                this.$el.find('.send_payment_cancel').click(function () {
                    self.set_ipaymu_status(line, 'retry', true);
                });
                this.$el.find('.send_force_done').click(function () {
                    self.set_ipaymu_status(line, 'done', true);
                });
            }
        },

        setQrCode: function(qrCode) {
            this.pos.get_order().QrCode = qrCode || false;
            this.renderElement();
            this.pos.send_current_order_to_customer_facing_display();
        },

        renderElement: function(scrollbottom) {
            this._super(scrollbottom);
            if (this.pos.get_order() && this.pos.get_order().QrCode) {
                $(".payment-numpad").hide();
                $(".payment-buttons").hide();
            }
        },

        set_ipaymu_status: function(line, ipaymu_status, cancel_flow) {
            if (cancel_flow) {
                clearTimeout(line.payment_timer);
                clearInterval(this.check_status);
                this.setQrCode();
            }
            line.set_payment_status(ipaymu_status);
            this.pos.get_order().save_to_db();
            this.order_changes();
            this.render_paymentlines();
        },

        send_ipaymu_request: function(paymentline) {
            var self = this;
            rpc.query({
                model: "pos_ipaymu.configuration",
                method: "get_qr_code",
                args: [{
                    amount: paymentline.amount,
                    uniqid: this.pos.get_order().name.match(/[0-9]/gm).join(""),
                    ipaymu_config_id: paymentline.cashregister.journal.pos_ipaymu_config_id[0],
                }]
            })
            .then(function(response) {
                if (response.Status === 'AuthorisationError') {
                    self.gui.show_popup('alert', {
                        title: _t('Ipaymu authorisation failed'),
                        body: _.str.sprintf(
                                _t('Make sure you are using a valid Ipaymu API key in your configuration.')
                                ),
                    });
                } else {
                    self.setQrCode(response.QrCode);
                    self.check_status = setInterval(function() {
                        rpc
                            .query({
                                model: "pos_ipaymu.configuration",
                                method: "get_status_payment",
                                args: [{
                                    trx_id: response.TrxId,
                                    ipaymu_config_id: paymentline.cashregister.journal.pos_ipaymu_config_id[0],
                                }]
                            })
                        .then(function(response) {
                            if (paymentline.payment_status !== 'retry') {
                                if (response.Status === 'waitingScan') {
                                    self.set_ipaymu_status(paymentline, 'waitingCard', false);
                                } else if (response.Status === 'done') {
                                    self.set_ipaymu_status(paymentline, 'done', true);
                                } else if (response.Status === 'retry') {
                                    self.set_ipaymu_status(paymentline, 'retry', true);
                                }
                            }
                        });
                    }, 2000);
                }
            });

        },

        /**
         * @override
         * If the selected payment method is linked to ipaymu with an active payment line
         * linked to it, An error should be shown.
         */
        click_paymentmethods: function(id) {
            var order = this.pos.get_order()
            if (order.get_paymentlines()
                    .some(function(pl) {
                        if (pl.cashregister.journal.pos_ipaymu_config_id && pl.payment_status) {
                            return !['done'].includes(pl.payment_status);
                        }
                    })) {
                this.gui.show_popup('error',{
                    'title': _t('Error'),
                    'body':  _t('There is already an ipaymu payment in progress.'),
                });
            } else {
                this._super(id);
                var cashregister = _.find(this.pos.cashregisters, function(cr) {
                    return cr.journal_id[0] === id;
                });
                if (cashregister.journal.pos_ipaymu_config_id) {
                    var payment_line = order.selected_paymentline;
                    this.set_ipaymu_status(payment_line, 'pending', false);
                    payment_line.set_amount(order.get_due());
                    this.render_paymentlines();
                    this.order_changes();
                }
            }
        },

        // before validating, get rid of any paymentlines that are waiting on ipaymu.
        validate_order: function(force_validation) {
            clearInterval(check_status);
            this._super(force_validation);
        }
    });
});
