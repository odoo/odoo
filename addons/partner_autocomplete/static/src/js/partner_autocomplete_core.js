odoo.define('partner.autocomplete.core', function (require) {
    'use strict';

    var rpc = require('web.rpc');
    var concurrency = require('web.concurrency');

    var core = require('web.core');
    // var _t = core._t;

    return {
        _dropPrevious: new concurrency.DropPrevious(),

        /**
         * Check connectivity
         * @returns {boolean}
         */
        isOnline: function () {
            return navigator && navigator.onLine;
        },

        /**
         * Sanitize search value by removing all not alphanumeric
         *
         * @param search_value
         * @returns {string}
         * @private
         */
        _sanitizeVAT: function (search_value) {
            return search_value ? search_value.replace(/[^A-Za-z0-9]/g, '') : '';
        },

        /**
         * Check if searched value is possibly a VAT : 2 first chars = alpha + min 5 numbers
         *
         * @param search_val
         * @returns {boolean}
         * @private
         */
        _isVAT: function (search_val) {
            var str = this._sanitizeVAT(search_val);
            return checkVATNumber(str).valid_vat
        },

        /**
         * Validate: Not empty and length > 1
         *
         * @param search_val
         * @returns {*|boolean}
         * @private
         */
        validateSearchTerm: function (search_val) {
            return search_val && search_val.length > 1;
        },

        /**
         * Get list of companies via Clearbit Autocomplete API
         *
         * @param value
         * @returns {*|{readyState, getResponseHeader, getAllResponseHeaders, setRequestHeader, overrideMimeType, statusCode, abort}}
         * @private
         */
        autocomplete: function (value) {
            if (this._isVAT(value)) {
                return this.getVatSuggestions(value);
            } else {
                return this.getClearbitSuggestions(value);
            }
        },

        getVatSuggestions: function (value) {
            var self = this;
            var def = $.Deferred();

            rpc.query({
                model: 'res.partner',
                method: "read_by_vat",
                args: [value],
            }).then(function (vat_match) {
                if(vat_match){
                    vat_match.logo = vat_match.logo || '';
                    vat_match.label = vat_match.name;
                    vat_match.description = vat_match.vat;

                    if (!vat_match.domain) {
                        // vat_match.description += ' ' + _t('(source: VIES-VAT)');

                        self.getClearbitSuggestions(vat_match.name, true).then(function (suggestions) {
                            suggestions.map(function(suggestion){
                                suggestion.company_data_id = vat_match.company_data_id;
                            });
                            suggestions.unshift(vat_match);
                            def.resolve(suggestions);
                        });
                    } else def.resolve([vat_match]);
                } else def.reject()
            });

            this._dropPrevious.add(def);
            return def;
        },

        getClearbitSuggestions: function (value, addSource) {
            var def = $.ajax({
                url: _.str.sprintf('https://autocomplete.clearbit.com/v1/companies/suggest?query=%s', value),
                type: 'GET',
                dataType: 'json'
            }).then(function(suggestions){
                suggestions.map(function(suggestion){
                    suggestion.label = suggestion.name;
                    suggestion.description = suggestion.domain;
                    // if( addSource) suggestion.description += ' ' + _t('(source: Clearbit)');
                    return suggestion;
                });
                return suggestions;
            });

            this._dropPrevious.add(def);
            return def;
        },

        /**
         * Get the company logo as Base 64 image from domain
         *
         * @param company_domain
         * @returns {Promise}
         * @private
         */
        getCompanyLogo: function (company_domain) {
            var url = 'https://logo.clearbit.com/' + company_domain;
            return this._getBase64Image(url).then(function (base64Image) {
                // base64Image equals "data:" if image not available on given url
                return base64Image ? base64Image.replace(/^data:image[^;]*;base64,?/, '') : false;
            });
        },

        /**
         * Get enrichment data
         *
         * @param company_domain
         * @returns Promise
         * @private
         */
        enrichCompany: function (company_domain, company_data_id) {
            return rpc.query({
                model: 'res.partner',
                method: 'enrich_company',
                args: [company_domain, company_data_id],
            });
        },

        /**
         * Get enriched data + logo before populating partner form
         * @param company
         * @returns Promise
         */
        getCreateData: function (company) {
            var def = $.Deferred();

            if(company._formatted){
                def.resolve({
                    company: company._formatted,
                    logo: false
                });
            }
            else {
                // Fetch additionnal company info via Autocomplete Enrichment API
                var enrichPromise = this.enrichCompany(company.domain, company.company_data_id);

                // Get logo
                var logoPromise = this.getCompanyLogo(company.domain);

                $.when(enrichPromise, logoPromise).done(function (company_data, logo) {
                    def.resolve({
                        company: company_data,
                        logo: logo
                    });
                });
            }

            return def;
        },

        /**
         * Returns a deferred which will be resolved with the base64 data of the
         * image fetched from the given url.
         *
         * @private
         * @param {string} url - the url where to find the image to fetch
         * @returns {Deferred<string>}
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


    }
});
