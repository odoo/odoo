// Part of web_progress. See LICENSE file for full copyright and licensing details.
odoo.define('web.progress.bar', function (require) {
"use strict";

/**
 * Display Progress Bar when blocking UI
 */

var core = require('web.core');
var Widget = require('web.Widget');
var framework = require('web.framework');
var session = require('web.session');
var DataImport = require('base_import.import').DataImport;
const genericRelayEvents = require('web.progress.ajax').genericRelayEvents;
const findContext = require('web.progress.ajax').findContext;
var localStorage = require('web.local_storage');

var _t = core._t;
var QWeb = core.qweb;
var progress_timeout = 5000;
var progress_timeout_warn = progress_timeout*2;
var framework_blockUI = framework.blockUI;
var framework_unblockUI = framework.unblockUI;


var ProgressBar = Widget.extend({
    template: "WebProgressBar",
    progress_timer: false,
    events: {
        "click .progress_style": "setStyleClick",
    },
    style_localstorage_key: 'web_progress_style',
    init: function(parent, code, $spin_container) {
        this._super(parent);
        this.progress_code = code;
        this.$spin_container = $spin_container;
        this.systray = !$spin_container;
        this.cancel_html = QWeb.render('WebProgressBarCancel', {});
        this.cancel_confirm_html = QWeb.render('WebProgressBarCancelConfirm', {})
        this.style = localStorage.getItem(this.style_localstorage_key);
        if (!session.is_system || !this.style) {
            this.style = 'standard';
        }
    },
    start: function() {
        this.$progress_outline = this.$();
        this.$progress_frame = this.$("#progress_frame");
        this.$progress_message = this.$("#progress_message");
        this.$progress_time_eta = this.$("#progress_time_eta");
        this.$progress_time_eta2 = this.$("#progress_time_eta2");
        this.$progress_cancel = this.$("#progress_cancel");
        this.$progress_percent = this.$("#progress_percent");
        this.$progress_bar = this.$("#progress_bar");
        this.$progress_user = this.$("#progress_user");
        this.all_elements = [
            this.$progress_outline,
            this.$progress_frame,
            this.$progress_message,
            this.$progress_time_eta,
            this.$progress_time_eta2,
            this.$progress_cancel,
            this.$progress_percent,
            this.$progress_bar,
            this.$progress_user,
        ]
        this.setStyle(this.style);
        core.bus.on('rpc_progress_set_code', this, this.defineProgressCode);
        core.bus.on('rpc_progress', this, this.showProgress)
    },
    setStyleClick: function(event) {
        name = event.target.id;
        this.setStyle(name);
        event.stopPropagation();
    },
    setStyle: function(name) {
        if (!session.is_system) {
            this.$("#progress_style").css("visibility", 'hidden');
            // styles changeable only for admins
            return;
        }
        if (this.style && this.style !== name) {
            this.removeStyle(this.style);
            if (this.last_progress_list) {
                this.style = name;
                this.showProgress(this.last_progress_list)
            }
        }
        _.invoke(this.all_elements, 'addClass', name);
        this.style = name;
        localStorage.setItem(this.style_localstorage_key, name);
    },
    removeStyle: function(name) {
        _.invoke(this.all_elements, 'removeClass', name);
    },
    defineProgressCode: function(progress_code) {
        var self = this;
        if (!this.progress_code) {
            this.progress_code = progress_code;
            self._setTimeout();
            self._getProgressViaRPC();
        }
    },
    showProgress: function(progress_list) {
        this.last_progress_list = progress_list
        var self = this;
        var top_progress = progress_list[0];
        var progress_code = top_progress.code;
        var uid = session.uid;
        var is_system = session.is_system;
        if (this.progress_code !== progress_code || !is_system && uid !== top_progress.uid) {
            return;
        }
        if (top_progress.style) {
            this.setStyle(top_progress.style);
        }
        var progress_html = '<div class="text-left">';
        var progress = 0.0;
        var progress_total = 100;
        var cancellable = true;
        var level = '';
        _.each(progress_list, function(el) {
            var message = el.msg || "";
            progress_html += "<div>" + level + " " + el.progress + "%" + " (" + el.done + "/" + el.total + ")" + " " + message + "</div>"
            if (el.total) {
                progress += el.done / el.total * progress_total;
            }
            if (el.total) {
                progress_total /= el.total;
            }
            cancellable = cancellable && el.cancellable;
            level += level === '' ? '└' : '─';
            });
        progress_html += '</div>';
        if (top_progress['time_left']) {
            var eta_msg = '';
            var eta_msg2 = '';
            if (this.style !== 'standard') {
                eta_msg = top_progress['time_left'] + "<br/>" + top_progress['time_total']
            } else {
                eta_msg2 = _t("Est. time left: ") + top_progress['time_left'] + " / " + top_progress['time_total']
            }
            this.$progress_time_eta.html(eta_msg);
            this.$progress_time_eta2.html(eta_msg2);
        }
        self.$progress_outline.css("visibility", 'visible');
        if (self.$spin_container) {
            // this is main progress bar
            self.$spin_container.find(".oe_throbber_message").css("display", 'none');
            self.$spin_container.find(".o_message").css("display", 'none');
        } else {
            // this is a systray progress bar
            self.$progress_outline.addClass('o_progress_systray');
            self.$progress_message.removeClass('o_progress_message');
            self.$progress_message.addClass('o_progress_message_systray');
            self.$progress_user.css("visibility", 'visible');
            if (is_system) {
                self.$progress_user.html(top_progress.user);
            }
        }
        if (cancellable) {
            self._normalCancel();
        } else {
            self.$progress_cancel.html('');
        }
        var animation_timeout = progress_timeout;
        var old_progress = self.$progress_bar.data('progress');
        if (! old_progress) {
            old_progress = 0;
            animation_timeout = 1;
        }
        if (progress < old_progress) {
            // do it immediately if the progress goes backwards
            animation_timeout = 1;
        }
        self.$progress_bar.stop(true, true).animate({width: progress + '%'}, animation_timeout, "linear");
        self.$progress_bar.data('progress', progress)
        this.$progress_message.html(progress_html);
        this.$progress_percent.html(Number.parseFloat(progress).toFixed(2) + '%');
        self._cancelTimeout();
        self._setTimeout();
        },
    _confirmCancel: function () {
        var self = this;
        self.$progress_bar.data('ongoing_cancel', true);
        self.$progress_cancel.html(self.cancel_confirm_html);
        self.$progress_cancel.addClass('o_cancel_message');
        if (this.systray) {
            self.$progress_cancel.find('.btn').addClass('btn-default');
        } else {
        }
        var $progress_cancel_confirm_yes = self.$progress_cancel.find('#progress_cancel_yes');
        var $progress_cancel_confirm_no = self.$progress_cancel.find('#progress_cancel_no');
        $progress_cancel_confirm_yes.off();
        $progress_cancel_confirm_yes.one('click', function (event) {
            event.stopPropagation();
            self._confirmCancelYes();
        });
        $progress_cancel_confirm_no.off();
        $progress_cancel_confirm_no.one('click', function (event) {
            event.stopPropagation();
            self.$progress_bar.data('ongoing_cancel', false);
            self._normalCancel();
        });
    },
    _confirmCancelYes: function () {
        var self = this;
        core.bus.trigger('rpc_progress_cancel', self.progress_code);
        self.$progress_cancel.html(_t("Cancelling..."));
        self.$progress_cancel.addClass('o_cancel_message');
    },
    _normalCancel: function () {
        var self = this;
        if (self.$progress_bar.data('ongoing_cancel')) {
            return;
        }
        self.$progress_cancel.html(self.cancel_html);
        self.$progress_cancel.removeClass('o_cancel_message');
        var $progress_cancel_confirm = self.$progress_cancel.find('#progress_cancel_confirm');
        $progress_cancel_confirm.off();
        $progress_cancel_confirm.one('click', function (event) {
            event.stopPropagation();
            self._confirmCancel();
        });
    },
    _setTimeout: function () {
        var self = this;
        if (!this.progress_timer) {
            this.progress_timer = setTimeout(function () {
                self._notifyTimeoutWarn();
            }, progress_timeout_warn);
        }
    },
    _cancelTimeout: function () {
        if (this.progress_timer) {
            this.$progress_bar.removeClass('o_progress_bar_timeout');
            this.$progress_bar.removeClass('o_progress_bar_timeout_destroy');
            clearTimeout(this.progress_timer);
            this.progress_timer = false;
        }
    },
    _notifyTimeoutWarn: function () {
        var self = this;
        this._getProgressViaRPC();
        this.$progress_bar.removeClass('o_progress_bar_timeout_destroy');
        this.$progress_bar.addClass('o_progress_bar_timeout');
        this.progress_timer = setTimeout(function () {
            self._notifyTimeoutDestr();
        }, progress_timeout_warn);
    },
    _notifyTimeoutDestr: function () {
        var self = this;
        this.$progress_bar.removeClass('o_progress_bar_timeout');
        this.$progress_bar.addClass('o_progress_bar_timeout_destroy');
        this.progress_timer = setTimeout(function () {
            core.bus.trigger('rpc_progress_destroy', self.progress_code);
        }, progress_timeout_warn);
        self.progress_timer = false;
    },
    _getProgressViaRPC: function () {
        var progress_code = this.progress_code;
        if (!progress_code) {
            return;
        }
        core.bus.trigger('rpc_progress_refresh', progress_code);
    },
});

var progress_bars = [];
var tm = false;

function addProgressBarToBlockedUI(progress_code=false) {
    removeProgressBarFrmBlockedUI();
    var $el = $('.o_progress_blockui');
    if ($el.length == 0) {
        $el = $(".oe_blockui_spin_container");
        if ($el.length == 0) {
            $el = $(".o_import_progress_dialog");
            if ($el.length == 0) {
                // wait for the state propagation
                tm = setTimeout(function () {
                    addProgressBarToBlockedUI(progress_code);
                }, 100);
                return;
            }
        }
    }
    tm = false;
    var progress_bar = new ProgressBar(false, progress_code, $el);
    progress_bars.push(progress_bar);
    progress_bar.appendTo($el);
}

function removeProgressBarFrmBlockedUI() {
    _.invoke(progress_bars, 'destroy');
    progress_bars = [];
    if (tm) {
        clearTimeout(tm);
    }
}
function blockUI() {
    var tmp = framework_blockUI();
    addProgressBarToBlockedUI();
    return tmp;
}

function unblockUI() {
    removeProgressBarFrmBlockedUI();
    return framework_unblockUI();
}

framework.blockUI = blockUI;
framework.unblockUI = unblockUI;

const DataImportWebProgress = DataImport.include({
    _onBatchStart: function () {
        const tmp = this._super(...arguments);
        addProgressBarToBlockedUI();
        return tmp;
    },
    _rpc: function (params, options) {
        const execute_import = options && options.shadow && params.method === 'execute_import';
        if (execute_import) {
            genericRelayEvents('/web/', 'call', params);
            const context = findContext(params);
            if (progress_bars.length === 1 && context.progress_code) {
                progress_bars[0].defineProgressCode(context.progress_code);
            }
        }
        return this._super(...arguments);
    }
})

return {
    blockUI: blockUI,
    unblockUI: unblockUI,
    ProgressBar: ProgressBar,
    progress_timeout: progress_timeout,
    addProgressBarToBlockedUI: addProgressBarToBlockedUI,
    removeProgressBarFrmBlockedUI: removeProgressBarFrmBlockedUI,
    DatImportWebProgress: DataImportWebProgress,
};

});
