odoo.define("pos_restaurant.tipping", function(require) {
"use strict";

var core = require("web.core");
var ScreenWidget = require("point_of_sale.screens").ScreenWidget;
var PosBaseWidget = require("point_of_sale.BaseWidget");
var chrome = require("point_of_sale.chrome");
var screens = require("point_of_sale.screens");
var PopupWidget = require("point_of_sale.popups");
var gui = require("point_of_sale.gui");
var rpc = require("web.rpc");
var utils = require("pos_restaurant.utils");
var framework = require("web.framework");

var qweb = core.qweb;
var _t = core._t;

var TippingWidget = PosBaseWidget.extend({
    template: "TippingWidget",

    start: function() {
        var self = this;
        this.$el.click(function() {
            self.gui.show_screen("tipping");
        });
    }
});

var OrderSearchWidget = PosBaseWidget.extend({
    template: "OrderSearchWidget",

    start: function() {
        var self = this;
        this.$el.click(function() {
            self.gui.show_screen("order_search");
        });
    }
});

chrome.Chrome.include({
    init: function() {
        this._super();
        this.widgets.push({
            name: "tipping",
            widget: TippingWidget,
            replace: ".placeholder-TippingWidget",
            condition: function(){ return this.pos.config.handle_tip_adjustments; },
        });
        this.widgets.push({
            name: "order_search",
            widget: OrderSearchWidget,
            replace: ".placeholder-OrderSearchWidget",
            condition: function(){ return this.pos.config.handle_tip_adjustments; },
        });
    }
});

var TippingScreenOrder = PosBaseWidget.extend({
    template: "TippingScreenOrder",

    init: function(parent, options) {
        this._super(parent, options);
        this.parent = parent;
        this.order = options.order;
        this.waiting_tips = [];
    },

    wait_for: function(milliseconds) {
        return new Promise(function(resolve, reject) {
            setTimeout(function() {
                resolve();
            }, milliseconds);
        });
    },

    renderElement: function() {
        var self = this;
        this._super();

        // don't allow to tip a tipped order again
        if (self.order.tip_is_finalized) {
            this.$el.click(function() {
                var $this = $(this);
                $this.addClass("highlight");
                self.gui.show_popup('alert', {
                    title: _t('Already tipped'),
                    body: _.str.sprintf(_t('%s has already been tipped.'), self.order.uid),
                    cancel: function () {
                        $this.removeClass("highlight");
                    }
                });
            });
        } else {
            this.$el.click(function() {
                var $this = $(this);
                $this.addClass("highlight");
                self.gui.show_popup("number", {
                    title: _t("Add Tip"),
                    value: self.format_currency_no_symbol(self.order.tip_amount),
                    confirm: function(value) {
                        // This will finalize the tip after a certain
                        // amount of time. This gives the user some
                        // time to correct any typo's he made.
                        value = Number(value);

                        var force_tip, cancel_tip;
                        var force_tip_promise = new Promise(function (resolve, reject) {
                            force_tip = resolve;
                            cancel_tip = reject;
                        });

                        if (self.cancel_previous_tip) {
                            console.log("cancelling previous promise");
                            self.cancel_previous_tip();
                        }

                        self.cancel_previous_tip = cancel_tip;
                        self.parent.force_pending_tippings.push(force_tip);
                        var tipping_promise = Promise.race([self.wait_for(60 * 1000), force_tip_promise]).then(function () {
                            console.log("tipping ", self.order.uid);
                            if (! self.order.tip_is_finalized) {
                                self.order.tip_is_finalized = true;
                                self.renderElement();
                                return rpc.query({
                                    model: "pos.order",
                                    method: "set_tip",
                                    args: [self.order.uid, value]
                                }).catch(function (error) {
                                    self.gui.show_popup('error-traceback',{
                                        title: error.data.message,
                                        body: error.data.debug
                                    });
                                });
                            } else {
                                return Promise.resolve();
                            }
                        });
                        self.parent.pending_tippings.push(tipping_promise);

                        self.order.is_tipped = true;
                        self.order.tip_is_finalized = false;
                        self.order.tip_amount = value;
                        self.order.amount_total = self.order.amount_total_without_tip + value;
                        self.renderElement();

                        var search_box = self.parent.el.querySelector(".searchbox input");
                        search_box.focus();

                        // search_box.select() doesn't work on iOS
                        search_box.setSelectionRange(0, search_box.value.length);

                        $this.removeClass("highlight");
                    },
                    cancel: function() {
                        $this.removeClass("highlight");
                    }
                });
            });
        }
    }
});

var TippingScreenWidget = ScreenWidget.extend({
    template: "TippingScreenWidget",
    auto_back: true,

    init: function(parent, options) {
        this._super(parent, options);
        this.filtered_confirmed_orders = [];
        this.force_pending_tippings = [];
        this.pending_tippings = [];
        console.log("cleared tipping timers");
        this.current_search = "";
    },

    show: function() {
        var self = this;
        this._super();

        // this screen is not related to orders, so hide this widget
        this.chrome.widget.order_selector.hide();

        this.filtered_confirmed_orders = this.pos.db.confirmed_orders;

        // re-render the template when showing it to have the
        // latest orders.
        this.renderElement();
        this.render_orders();

        this.$(".back").click(function() {
            self.gui.back();
        });

        var search_timeout = undefined;

        // use keydown because keypress isn't triggered for backspace
        this.$(".searchbox input").on("keydown", function() {
            var searchbox = this;
            clearTimeout(search_timeout);

            search_timeout = setTimeout(function() {
                if (self.current_search != searchbox.value) {
                    self.current_search = searchbox.value;
                    self.search(self.current_search);
                } else {
                }
            }, 70);
        });
    },

    render_orders: function() {
        var self = this;

        this.$el
            .find(".list-table-contents")
            .empty()
            .append(
                this.filtered_confirmed_orders.map(function(order) {
                    var tipping_order = new TippingScreenOrder(self, {
                        order: order
                    });
                    tipping_order.renderElement();
                    return tipping_order.$el;
                })
            );
    },

    search: function(term) {
        var self = this;
        this.filtered_confirmed_orders = utils.full_search(this.pos.db.confirmed_orders, term);
        this.render_orders();
    },

    force_tips: function() {
        console.log("force tips");
        this.force_pending_tippings.forEach(function (force) {
            force();
        });

        return Promise.all(this.pending_tippings);
    },

    close: function() {
        this._super();
        this.chrome.widget.order_selector.show();

        if (this.pos.config.iface_vkeyboard && this.chrome.widget.keyboard) {
            this.chrome.widget.keyboard.hide();
        }

        this.force_tips();
    }
});
gui.define_screen({ name: "tipping", widget: TippingScreenWidget });

gui.Gui.include({
    close: function() {
        var close_super = this._super.bind(this);
        this.screen_instances.tipping.force_tips().finally(function () {
            close_super();
        });
    }
});

var OrderSearchScreen = ScreenWidget.extend({
    template: "OrderSearchScreen",
    auto_back: true,

    init: function(parent, options) {
        this._super(parent, options);
        this.current_search = "";
        this.filtered_open_orders = [];
    },

    get_customer_name: function(db_order) {
        var partner_id = db_order.partner_id;
        if (!partner_id) {
            return "";
        } else {
            var partner = this.pos.db.get_partner_by_id(partner_id);
            return partner.name;
        }
    },

    show: function() {
        var self = this;
        this._super();

        // this screen is not related to orders, so hide this widget
        this.chrome.widget.order_selector.hide();

        this.filtered_open_orders = this.pos.db.get_unpaid_orders();

        // re-render the template when showing it to have the
        // latest orders.
        this.renderElement();
        this.render_orders();

        this.$(".back").click(function() {
            self.gui.back();
        });

        var search_timeout = undefined;

        // use keydown because keypress isn't triggered for backspace
        this.$(".searchbox input").on("keydown", function() {
            var searchbox = this;
            clearTimeout(search_timeout);
            search_timeout = setTimeout(function() {
                if (self.current_search != searchbox.value) {
                    self.current_search = searchbox.value;
                    self.search(self.current_search);
                }
            }, 70);
        });
    },

    render_orders: function() {
        var self = this;
        this.$el
            .find(".list-table-contents")
            .empty()
            .append(qweb.render("OrderSearchScreenOrders", {
                filtered_open_orders: this.filtered_open_orders,
                widget: this,
            }));

        this.$el.find('.list-table-contents > tr').click(function () {
            var uid = $(this).data('uid');
            // get_order_list() is overridden by pos_restaurant to
            // only return orders on the current table so use backbone
            // directly.
            var order = self.pos.get('orders').models.find(function (order) {
                return order.uid == uid;
            });

            var order_sync = Promise.resolve();
            if (order.table != self.pos.table) {
                // block the UI because orders will need to be synced
                // to the server first, and on a slow connection the
                // UI will be stuck on the table selection screen for
                // a second or 2
                framework.blockUI();
                self.pos.set_table(); // sync orders
                order_sync = self.pos.set_table(order.table);
            }

            order_sync.finally(function () {
                self.pos.gui.show_screen('products');

                // find the order again, the logic in set_table could
                // remove the original order and create a new one
                order = self.pos.get_order_list().find(function (order) {
                    return order.uid == uid;
                });
                self.pos.set_order(order);
                framework.unblockUI();
            });
        });
    },

    search: function(term) {
        var self = this;
        this.filtered_open_orders = this.pos.db.get_unpaid_orders();

        if (term) {
            this.filtered_open_orders = utils.full_search(
                this.filtered_open_orders,
                term,
                ['card_name', 'uid', 'amount_total']
            );
        }

        this.render_orders();
    },

    close: function() {
        this._super();
        this.chrome.widget.order_selector.show();

        if (this.pos.config.iface_vkeyboard && this.chrome.widget.keyboard) {
            this.chrome.widget.keyboard.hide();
        }
    }
});
gui.define_screen({ name: "order_search", widget: OrderSearchScreen });

var CancelPopupWidget = PopupWidget.extend({
    template:'CancelPopupWidget',
});
gui.define_popup({name:'cancel', widget: CancelPopupWidget});

var AuthorizeCardButton = screens.ActionButtonWidget.extend({
    template: 'AuthorizeCardButton',
    button_click: function(){
        var self = this;
        var order = this.pos.get_order();
        var payment_method = this.pos.payment_methods.find(function (method) {
            return method.payment_terminal;
        });

        order.add_paymentline(payment_method);
        var line = order.selected_paymentline;

        this.gui.show_popup("cancel", {
            title: _t("Waiting on authorization..."),
            body: _t("Please follow the instructions on the payment terminal."),
            cancel: function () {
                return payment_method.payment_terminal.send_payment_cancel(order, line.cid);
            },
        });
        payment_method.payment_terminal.send_payment_request(line.cid).then(function (payment_successful) {
            // Whatever payment method is used will display an
            // error if the amount could not be authorized, don't
            // close that.
            if (payment_successful) {
                self.gui.close_popup();
            }

            order.authorization_payment_method = payment_method;
            order.authorization_id = line.transaction_id;
            order.trigger('change', order);
        }).finally(function () {
            order.remove_paymentline(line);
        });
    },
});

screens.define_action_button({
    'name': 'auth_card_button',
    'widget': AuthorizeCardButton,
    'condition': function(){
        return this.pos.config.handle_tip_adjustments;
    },
});

return {
    TippingWidget: TippingWidget,
    TippingScreenWidget: TippingScreenWidget,
    OrderSearchScreen: OrderSearchScreen,
    AuthorizeCardButton: AuthorizeCardButton,
};
});
