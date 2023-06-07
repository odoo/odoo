/** @odoo-module alias=web.DomainSelectorDialog **/

import { _t } from "@web/core/l10n/translation";
import Dialog from "web.Dialog";
import Domain from "web.Domain";
import DomainSelector from "web.DomainSelector";

/**
 * @class DomainSelectorDialog
 */
export default Dialog.extend({
    custom_events: Object.assign({}, Dialog.prototype.custom_events, {
        domain_changed: "_onDomainChange",
    }),
    init: function (parent, model, domain, options) {
        this.model = model;
        this.newDomain = null;
        this.options = Object.assign({
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
                    this.trigger_up("domain_selected", {
                        domain: this.newDomain !== null ? this.newDomain : this.domainSelector.getDomain(),
                    });
                }},
                {text: _t("Discard"), close: true},
            ];
        }

        this._super(parent, Object.assign({}, {
            title: _t("Domain"),
            buttons: buttons,
        }, options || {}));
        this.domainSelector = new DomainSelector(this, model, Domain.prototype.arrayToString(domain), options);
    },
    start: function () {
        var self = this;
        this.opened().then(function () {
            // this restores default modal height (bootstrap) and allows field selector to overflow
            self.$el.css('overflow', 'visible').closest('.modal-dialog').css('height', 'auto');
        });
        return Promise.all([
            this._super.apply(this, arguments),
            this.domainSelector.appendTo(this.$el)
        ]);
    },
    /**
     * Called when the domain selector value is changed.
     *
     * @param {OdooEvent} ev
     */
    _onDomainChange: function (ev) {
        ev.stopPropagation();
        this.newDomain = ev.data.domain;
    },
});
