odoo.define('partner.autocomplete.core', function (require) {
    'use strict';

    var rpc = require('web.rpc');
    var concurrency = require('web.concurrency');
    
    return {
        _dropPrevious: new concurrency.DropPrevious(),

        /**
         * Check connectivity
         * @returns {boolean}
         */
        isOnline: function(){
            return navigator && navigator.onLine;
        },

        /**
         * Sanitize search value by removing all not alphanumeric
         *
         * @param search_value
         * @returns {string}
         * @private
         */
        _sanitizeVAT: function(search_value){
            return search_value ? search_value.replace(/[^A-Za-z0-9]/g, '') : '';
        },

        /**
         * Check if searched value is possibly a VAT : 2 first chars = alpha + min 5 numbers
         *
         * @param search_val
         * @returns {boolean}
         * @private
         */
        _isVAT: function(search_val) {
            var str = this._sanitizeVAT(search_val);
            var regex = /^[A-Za-z]{2}\d{5,}$/g;

            return str && regex.test(str);
        },

        /**
         * Validate: Not empty and length > 1
         *
         * @param search_val
         * @returns {*|boolean}
         * @private
         */
        validateSearchTerm: function (search_val) {
            return search_val && search_val.length > 1 && !this._isVAT(search_val);
        },

        /**
         * Get list of companies via Clearbit Autocomplete API
         *
         * @param value
         * @returns {*|{readyState, getResponseHeader, getAllResponseHeaders, setRequestHeader, overrideMimeType, statusCode, abort}}
         * @private
         */
        autocomplete: function (value) {
            var def = $.ajax({
                url: _.str.sprintf('https://autocomplete.clearbit.com/v1/companies/suggest?query=%s', value),
                type: 'GET',
                dataType: 'json'
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
        enrichCompany: function (company_domain) {
            return rpc.query({
                model: 'res.partner',
                method: 'enrich_company',
                args: [company_domain],
            });
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
