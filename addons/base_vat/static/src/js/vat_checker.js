odoo.define('base.vat.vat_checker', function (require) {
    'use strict';

    var core = require('web.core');

    var AbstractField = require('web.AbstractField');
    var fieldRegistry = require('web.field_registry');

    var _t = core._t;

    var rpc = require('web.rpc');
    var concurrency = require('web.concurrency');

    var VATChecker = AbstractField.extend({
        className: 'o_field_vat_checker',
        resetOnAnyFieldChange: true,
        currentValue: null,

        /**
         * @constructor
         * @see AbstractField.init
         */
        init: function () {
            this._super.apply(this, arguments);
            if (this.mode === 'edit') {
                this.currentValue = this.record.data.vat;
                this.dropPrevious = new concurrency.DropPrevious();
            }
        },

        /**
         * @override
         */
        start: function () {
            if (this.mode === 'edit') {
                this.$indicator = $('<i/>');
                this.$el.append(this.$indicator);
                this._popover.init(this.$el);
                if (this.record.data.vat_validation_state) this._setState(this.record.data.vat_validation_state);
            }
            return this._super.apply(this, arguments);
        },

        /**
         * @override
         */
        reset: function (state) {
            var self = this;
            var oldVat = this.currentValue;
            var newVat = state.data.vat;
            this.currentValue = newVat;

            if (!newVat) {
                this._setState('hide');
            } else {
                if (oldVat !== newVat) {
                    var sanitized = this._sanitizeVAT(newVat);
                    if (this._isVAT(sanitized)) {
                        self._setState('loading');

                        this._checkVATValidity(sanitized).then(function (validity) {
                            if (validity.found_format) {
                                if (validity.existing) self._setState('valid', validity.extra_msg);
                                else {
                                    if (validity.format) self._setState('company_not_found');
                                    else self._setState('invalid_format', validity.extra_msg);
                                }
                            } else self._setState('unknown_country_code', validity.extra_msg);
                        });
                    } else {
                        self._setState('invalid_format', _t('2 letters followed by 2 to 12 alphanumerics'));
                    }
                }
            }

            return this._super.apply(this, arguments);
        },

        /**
         * @override
         */
        destroy: function () {
            this._popover.destroy();
            return this._super.apply(this, arguments);
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Internal object to manage the popover
         */
        _popover: {
            $el: false,
            autoHideDelay: 3000,
            init: function ($el) {
                var self = this;
                this.$el = $el;
                this.$el.popover({
                    placement: 'top',
                    trigger: 'manual hover',
                    html: true,
                });
                this.$el.on('shown.bs.popover', function () {
                    var tip = $(self.getAPI().getTipElement());
                    self.id = tip.attr('id') || self.id;
                    tip.addClass('text-center');
                });
                return this;
            },
            getAPI: function () {
                return this.$el.data('bs.popover');
            },
            destroy: function () {
                if (this.id) $('#' + this.id).remove();
            },
            show: function () {
                this.$el.popover('show');
                return this;
            },
            hide: function () {
                this.$el.popover('hide');
                return this;
            },
            set: function (message) {
                this.getAPI().config.content = message;
                return this;
            },
            autoShowHide: function () {
                this.show();
                if (this.timeout) clearTimeout(this.timeout);
                this.timeout = setTimeout(this.hide.bind(this), this.autoHideDelay);
                return this;
            }
        },

        /**
         * Call RPC to check advanced formatting and valididty of VAT
         *
         * @param {string} vat
         * @returns {Deferred}
         * @private
         */
        _checkVATValidity: function (vat) {
            var def = rpc.query({
                model: 'res.partner',
                method: 'check_vat_rpc',
                args: [vat],
            }, {
                shadow: true,
            });

            return this.dropPrevious.add(def);
        },

        /**
         * Fast check format of string match a VAT number
         * Must be 2 Characters + 2 to 12 Alphanumerics
         *
         * @param {string} vat
         * @returns {Boolean}
         * @private
         */
        _isVAT: function (vat) {
            return vat && vat.match(/^[a-zA-Z]{2}[a-zA-Z0-9]{2,12}$/);
        },

        /**
         * Sanitize search value by removing all not alphanumeric
         *
         * @param {string} vat
         * @returns {string}
         * @private
         */
        _sanitizeVAT: function (vat) {
            return vat ? vat.replace(/[^A-Za-z0-9]/g, '') : '';
        },

        /**
         * Update UI to show State Icon and title tooltip information
         * + Set new value into DB field
         *
         * @param {string} state
         * @param {string} extra_msg
         * @private
         */
        _setState: function (state, extra_msg) {
            var classes = 'fa fa-lg ';
            var title;
            var db_state = state;

            this._popover.hide();

            switch (state) {
                case 'valid':
                    classes += "fa-check-circle text-success";
                    title = "<b>VAT number is valid</b>";
                    if (extra_msg) title += "<br/>Company : %s";
                    break;
                case 'company_not_found':
                    classes += "fa-question-circle text-warning";
                    title = "<b>No company found with this VAT number</b>";
                    break;
                case 'unknown_country_code':
                    classes += "fa-question-circle text-muted";
                    title = "<b>No VAT formatting found for the country code</b>";
                    if (extra_msg) title += " : %s";
                    break;
                case 'invalid_format':
                    classes += "fa-exclamation-triangle text-danger";
                    title = "<b>Incorrect VAT number format</b>";
                    if (extra_msg) title += "<br/>Expected format: %s";
                    break;
                case 'timeout':
                    classes += "fa-clock-o text-danger";
                    title = "<b>VIES-VAT is not responding, please try again later</b>";
                    break;
                case 'error':
                    classes += "fa-frown-o text-danger";
                    title = "<b>Sorry, an error occurred</b>";
                    if (extra_msg) title += "<br/>%s";
                    break;
                case 'loading':
                    classes += "fa-spinner fa-spin text-muted";
                    title = "";
                    db_state = false;
                    break;
            }

            this.$indicator.removeClass().addClass(classes);
            if (title) this._popover.set(_.str.sprintf(_t(title), extra_msg)).autoShowHide();
            if (db_state) this._setValue(db_state);
        },
    });

    fieldRegistry.add('vat_checker', VATChecker);

    return VATChecker;
});
