odoo.define("web.DomainSelectorDialog", function (require) {
"use strict";

var core = require("web.core");
var Dialog = require("web.Dialog");
var DomainSelector = require("web.DomainSelector");

var _t = core._t;

/**
 * @class DomainSelectorDialog
 */
return Dialog.extend({
    init: function (parent, model, domain, options) {
        this.model = model;
        this.options = _.extend({
            readonly: true,
            debugMode: false,
        }, options || {});

        var buttons;
        if (this.options.readonly) {
            buttons = [
                {text: _t("Close"), close: true},
            ];
        } else {
            buttons = [
                {text: _t("Save"), classes: "btn-primary", close: true, click: function () {
                    this.trigger_up("domain_selected", {domain: this.domainSelector.getDomain()});
                }},
                {text: _t("Discard"), close: true},
            ];
        }

        this._super(parent, _.extend({}, {
            title: _t("Domain"),
            buttons: buttons,
        }, options || {}));

        this.domainSelector = new DomainSelector(this, model, domain, options);
    },
    start: function () {
        var self = this;
        this.opened().then(function () {
            // this restores default modal height (bootstrap) and allows field selector to overflow
            self.$el.css('overflow', 'visible').closest('.modal-dialog').css('height', 'auto');
        });
        return $.when(
            this._super.apply(this, arguments),
            this.domainSelector.appendTo(this.$el)
        );
    },
});
});
