odoo.define('mail.MobileUndobar', function (require) {
"use strict";

var Widget = require('web.Widget');

return Widget.extend({
    template: 'MobileUndobar',
    events: {
        'click .o_btn_undo': '_onClickButtonUndo'
    },
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.message = options.message || '';
        this.delay = options.delay || 1000;
        this.onComplete = options.complete;
        this.onCancel = options.cancel;
        this._timeout = false;
    },
    show: function () {
        var self = this;
        this.appendTo($("body"));
        this._timeout = setTimeout(function () {
            if (self.onComplete) {
                self.onComplete();
                self.destroy();
            }
        }, this.delay);
    },
    _onClickButtonUndo: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        if (this.onCancel) {
            this.onCancel();
        }
        clearTimeout(this._timeout);
        this.destroy();
    }
});
});