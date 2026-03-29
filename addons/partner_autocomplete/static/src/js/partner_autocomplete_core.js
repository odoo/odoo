/* global checkVATNumber */
odoo.define('partner.autocomplete.Mixin', function (require) {
'use strict';

var concurrency = require('web.concurrency');

var core = require('web.core');
var Qweb = core.qweb;
var utils = require('web.utils');
var _t = core._t;

/**
 * This mixin only works with classes having EventDispatcherMixin in 'web.mixins'
 */
var PartnerAutocompleteMixin = {
    _dropPreviousOdoo: new concurrency.DropPrevious(),
    _dropPreviousClearbit: new concurrency.DropPrevious(),
    _timeout : 1000, // Timeout for Clearbit autocomplete in ms

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Get list of companies via Autocomplete API
     *
     * @param {string} value
     * @returns {Promise}
     * @private
     */
    _autocomplete: function (value) {
        var self = this;
        value = value.trim();
        var isVAT = this._isVAT(value);
        var odooSuggestions = [];
        var clearbitSuggestions = [];
        return new Promise(function (resolve, reject) {
            var odooPromise = self._getOdooSuggestions(value, isVAT).then(function (suggestions){
                odooSuggestions = suggestions;
            });

            // Only get Clearbit suggestions if not a VAT number
            var clearbitPromise = isVAT ? false : self._getClearbitSuggestions(value).then(function (suggestions){
                clearbitSuggestions = suggestions;
            });

            var concatResults = function () {
                // Add Clearbit result with Odoo result (with unique domain)
                if (clearbitSuggestions && clearbitSuggestions.length) {
                    var websites = odooSuggestions.map(function (suggestion) {
                        return suggestion.website;
                    });
                    clearbitSuggestions.forEach(function (suggestion) {
                        if (websites.indexOf(suggestion.domain) < 0) {
                            websites.push(suggestion.domain);
                            odooSuggestions.push(suggestion);
                        }
                    });
                }

                odooSuggestions = _.filter(odooSuggestions, function (suggestion) {
                    return !suggestion.ignored;
                });
                _.each(odooSuggestions, function(suggestion){
                delete suggestion.ignored;
                });
                return resolve(odooSuggestions);
            };

            self._whenAll([odooPromise, clearbitPromise]).then(concatResults, concatResults);
        });

    },

    /**
     * Get enrichment data
     *
     * @param {Object} company
     * @param {string} company.website
     * @param {string} company.partner_gid
     * @param {string} company.vat
     * @returns {Promise}
     * @private
     */
    _enrichCompany: function (company) {
        return this._rpc({
            model: 'res.partner',
            method: 'enrich_company',
            args: [company.website, company.partner_gid, company.vat],
        });
    },

    /**
     * Get the company logo as Base 64 image from url
     *
     * @param {string} url
     * @returns {Promise}
     * @private
     */
    _getCompanyLogo: function (url) {
        return this._getBase64Image(url).then(function (base64Image) {
            // base64Image equals "data:" if image not available on given url
            return base64Image ? base64Image.replace(/^data:image[^;]*;base64,?/, '') : false;
        }).catch(function () {
            return false;
        });
    },

    /**
     * Get enriched data + logo before populating partner form
     *
     * @param {Object} company
     * @returns {Promise}
     */
    _getCreateData: function (company) {
        var self = this;

        var removeUselessFields = function (company) {
            var fields = 'label,description,domain,logo,legal_name,ignored,email,skip_enrich'.split(',');
            fields.forEach(function (field) {
                delete company[field];
            });

            var notEmptyFields = "country_id,state_id".split(',');
            notEmptyFields.forEach(function (field) {
                if (!company[field]) delete company[field];
            });
        };

        return new Promise(function (resolve) {
            // Fetch additional company info via Autocomplete Enrichment API
            var enrichPromise = !company.skip_enrich ? self._enrichCompany(company) : false;

            // Get logo
            var logoPromise = company.logo ? self._getCompanyLogo(company.logo) : false;
            self._whenAll([enrichPromise, logoPromise]).then(function (result) {
                var company_data = result[0];
                var logo_data = result[1];

                // The vat should be returned for free. This is the reason why
                // we add it into the data of 'company' even if an error such as
                // an insufficient credit error is raised. 
                if (company_data.error && company_data.vat) {
                    company.vat = company_data.vat;
                }

                if (company_data.error) {
                    if (company_data.error_message === 'Insufficient Credit') {
                        self._notifyNoCredits();
                    } else if (company_data.error_message === 'No Account Token') {
                        self._notifyAccountToken();
                    } else {
                        self.displayNotification({ message: company_data.error_message });
                    }
                    company_data = company;
                }

                if (_.isEmpty(company_data)) {
                    company_data = company;
                }

                // Delete attribute to avoid "Field_changed" errors
                removeUselessFields(company_data);

                // Assign VAT coming from parent VIES VAT query
                if (company.vat) {
                    company_data.vat = company.vat;
                }
                resolve({
                    company: company_data,
                    logo: logo_data
                });
            });
        });
    },

    /**
     * Check connectivity
     *
     * @returns {boolean}
     */
    _isOnline: function () {
        return navigator && navigator.onLine;
    },

    /**
     * Validate: Not empty and length > 1
     *
     * @param {string} search_val
     * @param {string} onlyVAT : Only valid VAT Number search
     * @returns {boolean}
     * @private
     */
    _validateSearchTerm: function (search_val, onlyVAT) {
        if (onlyVAT) return this._isVAT(search_val);
        else return search_val && search_val.length > 2;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Returns a promise which will be resolved with the base64 data of the
     * image fetched from the given url.
     *
     * @private
     * @param {string} url : the url where to find the image to fetch
     * @returns {Promise}
     */
    _getBase64Image: function (url) {
        return new Promise(function (resolve, reject) {
            var xhr = new XMLHttpRequest();
            xhr.onload = function () {
                utils.getDataURLFromFile(xhr.response).then(resolve);
            };
            xhr.open('GET', url);
            xhr.responseType = 'blob';
            xhr.onerror = reject;
            xhr.send();
        });
    },

    /**
     * Use Clearbit Autocomplete API to return suggestions
     *
     * @param {string} value
     * @returns {Promise}
     * @private
     */
    _getClearbitSuggestions: function (value) {
        var url = 'https://autocomplete.clearbit.com/v1/companies/suggest?query=' + value;
        var def = $.ajax({
            url: url,
            dataType: 'json',
            timeout: this._timeout,
            success: function (suggestions) {
                suggestions.map(function (suggestion) {
                    suggestion.label = suggestion.name;
                    suggestion.website = suggestion.domain;
                    suggestion.description = suggestion.website;
                    return suggestion;
                });
                return suggestions;
            },
        });

        return this._dropPreviousClearbit.add(def);
    },

    /**
     * Use Odoo Autocomplete API to return suggestions
     *
     * @param {string} value
     * @param {boolean} isVAT
     * @returns {Promise}
     * @private
     */
    _getOdooSuggestions: function (value, isVAT) {
        var method = isVAT ? 'read_by_vat' : 'autocomplete';

        var def = this._rpc({
            model: 'res.partner',
            method: method,
            args: [value],
        }, {
            shadow: true,
        }).then(function (suggestions) {
            suggestions.map(function (suggestion) {
                suggestion.logo = suggestion.logo || '';
                suggestion.label = suggestion.legal_name || suggestion.name;
                if (suggestion.vat) suggestion.description = suggestion.vat;
                else if (suggestion.website) suggestion.description = suggestion.website;

                if (suggestion.country_id && suggestion.country_id.display_name) {
                    if (suggestion.description) suggestion.description += _.str.sprintf(' (%s)', suggestion.country_id.display_name);
                    else suggestion.description += suggestion.country_id.display_name;
                }

                return suggestion;
            });
            return suggestions;
        });

        return this._dropPreviousOdoo.add(def);
    },
    /**
     * Check if searched value is possibly a VAT : 2 first chars = alpha + min 5 numbers
     *
     * @param {string} search_val
     * @returns {boolean}
     * @private
     */
    _isVAT: function (search_val) {
        var str = this._sanitizeVAT(search_val);
        return checkVATNumber(str);
    },

    /**
     * Sanitize search value by removing all not alphanumeric
     *
     * @param {string} search_value
     * @returns {string}
     * @private
     */
    _sanitizeVAT: function (search_value) {
        return search_value ? search_value.replace(/[^A-Za-z0-9]/g, '') : '';
    },

    /**
     * Utility to wait for multiple promises
     * Promise.all will reject all promises whenever a promise is rejected
     * This utility will continue
     *
     * @param {Promise[]} promises
     * @returns {Promise}
     * @private
     */
    _whenAll: function (promises) {
        return Promise.all(promises.map(function (p) {
            return Promise.resolve(p);
        }));
    },

    /**
     * @private
     * @returns {Promise}
     */
    _notifyNoCredits: function () {
        var self = this;
        return this._rpc({
            model: 'iap.account',
            method: 'get_credits_url',
            args: ['partner_autocomplete'],
        }).then(function (url) {
            var title = _t('Not enough credits for Partner Autocomplete');
            var content = Qweb.render('partner_autocomplete.insufficient_credit_notification', {
                credits_url: url
            });
            self.displayNotification({
                title,
                message: utils.Markup(content),
                className: 'o_partner_autocomplete_no_credits_notify',
            });
        });
    },

    _notifyAccountToken: function () {
        var self = this;
        return this._rpc({
            model: 'iap.account',
            method: 'get_config_account_url',
            args: []
        }).then(function (url) {
            var title = _t('IAP Account Token missing');
            if (url){
                var content = Qweb.render('partner_autocomplete.account_token', {
                    account_url: url
                });
                self.displayNotification({
                    title,
                    message: utils.Markup(content),
                    className: 'o_partner_autocomplete_no_credits_notify',
                });
            }
            else {
                self.displayNotification({ title });
            }
        });
    },
};

return PartnerAutocompleteMixin;

});
