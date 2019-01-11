odoo.define('partner.autocomplete.core', function (require) {
'use strict';

var rpc = require('web.rpc');
var concurrency = require('web.concurrency');

return {
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
     * @returns {Deferred}
     * @private
     */
    autocomplete: function (value) {
        value = value.trim();
        var def = $.Deferred(),
            isVAT = this._isVAT(value),
            odooSuggestions = [],
            clearbitSuggestions = [];

        var odooPromise = this._getOdooSuggestions(value, isVAT).then(function (suggestions){
            odooSuggestions = suggestions;
        });

        // Only get Clearbit suggestions if not a VAT number
        var clearbitPromise = isVAT ? false : this._getClearbitSuggestions(value).then(function (suggestions){
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
            return def.resolve(odooSuggestions);
        };

        this._whenAll([odooPromise, clearbitPromise]).then(concatResults, concatResults);

        return def;
    },

    /**
     * Get enrichment data
     *
     * @param {Object} company
     * @returns {Deferred}
     * @private
     */
    enrichCompany: function (company) {
        return rpc.query({
            model: 'res.partner',
            method: 'enrich_company',
            args: [company.website, company.partner_gid, company.vat],
        });
    },

    /**
     * Get the company logo as Base 64 image from url
     *
     * @param {string} url
     * @returns {Deferred}
     * @private
     */
    getCompanyLogo: function (url) {
        return this._getBase64Image(url).then(function (base64Image) {
            // base64Image equals "data:" if image not available on given url
            return base64Image ? base64Image.replace(/^data:image[^;]*;base64,?/, '') : false;
        });
    },

    /**
     * Get enriched data + logo before populating partner form
     *
     * @param {Object} company
     * @returns {Deferred}
     */
    getCreateData: function (company) {
        var removeUselessFields = function (company) {
            var fields = 'label,description,domain,logo,legal_name,ignored'.split(',');
            fields.forEach(function (field) {
                delete company[field];
            });

            var notEmptyFields = "country_id,state_id".split(',');
            notEmptyFields.forEach(function (field) {
                if (!company[field]) delete company[field];
            });
        };

        var def = $.Deferred();

        // Fetch additional company info via Autocomplete Enrichment API
        var enrichPromise = this.enrichCompany(company);

        // Get logo
        var logoPromise = company.logo ? this.getCompanyLogo(company.logo) : false;

        this._whenAll([enrichPromise, logoPromise]).always(function (company_data, logo_data){
            if (Array.isArray(company_data)) company_data = company_data[0];
            else company_data = {};

            if (Array.isArray(logo_data)) logo_data = logo_data[0];
            else logo_data = '';

            if (_.isEmpty(company_data)) company_data = company;

            // Delete attribute to avoid "Field_changed" errors
            removeUselessFields(company_data);

            // Assign VAT coming from parent VIES VAT query
            if (company.vat) company_data.vat = company.vat;
            def.resolve({
                company: company_data,
                logo: logo_data
            });
        });

        return def;
    },

    /**
     * Check connectivity
     *
     * @returns {boolean}
     */
    isOnline: function () {
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
    validateSearchTerm: function (search_val, onlyVAT) {
        if (onlyVAT) return this._isVAT(search_val);
        else return search_val && search_val.length > 2;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Returns a deferred which will be resolved with the base64 data of the
     * image fetched from the given url.
     *
     * @private
     * @param {string} url : the url where to find the image to fetch
     * @returns {Deferred}
     */
    _getBase64Image: function (url) {
        var def = $.Deferred();
        var xhr = new XMLHttpRequest();
        xhr.onload = function () {
            var reader = new FileReader();
            reader.onloadend = function () {
                def.resolve(reader.result);
            };
            reader.readAsDataURL(xhr.response);
        };
        xhr.open('GET', url);
        xhr.responseType = 'blob';
        xhr.onerror = def.reject.bind(def);
        xhr.send();
        return def;
    },

    /**
     * Use Clearbit Autocomplete API to return suggestions
     *
     * @param {string} value
     * @returns {Deferred}
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
     * @returns {Deferred}
     * @private
     */
    _getOdooSuggestions: function (value, isVAT) {
        var method = isVAT ? 'read_by_vat' : 'autocomplete';

        var def = rpc.query({
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
     * $.when will reject all promises whenever a promise is rejected
     * This utility will continue
     * Source : https://gist.github.com/fearphage/4341799
     *
     * @param array
     * @returns {*}
     * @private
     */
    _whenAll: function (array) {
        var slice = [].slice;

        var
            resolveValues = arguments.length === 1 && $.isArray(array)
                ? array
                : slice.call(arguments)
            , length = resolveValues.length
            , remaining = length
            , deferred = $.Deferred()
            , i = 0
            , failed = 0
            , rejectContexts = Array(length)
            , rejectValues = Array(length)
            , resolveContexts = Array(length)
            , value
        ;

        function updateFunc(index, contexts, values) {
            return function () {
                !(values === resolveValues) && failed++;
                deferred.notifyWith(
                    contexts[index] = this
                    , values[index] = slice.call(arguments)
                );
                if (!(--remaining)) {
                    deferred[(!failed ? 'resolve' : 'reject') + 'With'](contexts, values);
                }
            };
        }

        for (; i < length; i++) {
            if ((value = resolveValues[i]) && $.isFunction(value.promise)) {
                value.promise()
                    .done(updateFunc(i, resolveContexts, resolveValues))
                    .fail(updateFunc(i, rejectContexts, rejectValues))
                ;
            }
            else {
                deferred.notifyWith(this, value);
                --remaining;
            }
        }

        if (!remaining) {
            deferred.resolveWith(resolveContexts, resolveValues);
        }

        return deferred.promise();
    },
};
});
