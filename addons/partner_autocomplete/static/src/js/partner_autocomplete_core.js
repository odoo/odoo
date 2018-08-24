odoo.define('partner.autocomplete.core', function (require) {
'use strict';

var rpc = require('web.rpc');
var concurrency = require('web.concurrency');

// var core = require('web.core');
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
     * @param {string} search_value
     * @returns {string}
     * @private
     */
    _sanitizeVAT: function (search_value) {
        return search_value ? search_value.replace(/[^A-Za-z0-9]/g, '') : '';
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
        return checkVATNumber(str).valid_vat
    },

    /**
     * Validate: Not empty and length > 1
     *
     * @param {string} search_val
     * @returns {boolean}
     * @private
     */
    validateSearchTerm: function (search_val) {
        return search_val && search_val.length > 2;
    },

    /**
     * Get list of companies via Autocomplete API
     *
     * @param {string} value
     * @returns {Deferred}
     * @private
     */
    autocomplete: function (value) {
        if (this._isVAT(value)) {
            return this.getVatSuggestions(value);
        } else {
            return this.getNameSuggestions(value);
        }
    },

    /**
     * Get Suggestions, search by VAT number
     *
     * @param {string} value
     * @returns {Deferred}
     */
    getVatSuggestions: function (value) {
        var self = this;
        var def = $.Deferred();

        rpc.query({
            model: 'res.partner',
            method: "read_by_vat",
            args: [value],
        },{
            shadow: true,
        }).then(function (vat_match) {
            if (vat_match) {
                vat_match.logo = vat_match.logo || '';
                vat_match.label = vat_match.legal_name || vat_match.name;
                vat_match.description = vat_match.vat;

                if (!vat_match.website) {
                    self.getNameSuggestions(vat_match.name).then(function (suggestions) {
                        suggestions.map(function (suggestion) {
                            suggestion.vat = vat_match.vat;
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

    /**
     * Get Suggestions, search by name
     *
     * @param {string} value
     * @returns {Deferred}
     */
    getNameSuggestions: function (value) {
        var def = rpc.query({
            model: 'res.partner',
            method: "autocomplete",
            args: [value],
        },{
            shadow: true,
        }).then(function (suggestions) {
            suggestions.map(function (suggestion) {
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

        this._dropPrevious.add(def);
        return def;
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
            args: [company.website, company.company_data_id],
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
            var fields = 'label,description,logo,legal_name'.split(',');
            fields.forEach(function(field){
                delete company[field];
            });

            var notEmptyFields = "country_id,state_id,vat".split(',');
            notEmptyFields.forEach(function(field){
                if(!company[field]) delete company[field];
            });
        };

        var def = $.Deferred();

        // Fetch additional company info via Autocomplete Enrichment API
        var enrichPromise = company.company_data_id || !company.website ? company : this.enrichCompany(company);

        // Get logo
        var logoPromise = company.logo ? this.getCompanyLogo(company.logo) : false;

        // Delete attribute to avoid "Field_changed" errors
        // removeUselessFields(company);

        $.when(enrichPromise, logoPromise).done(function (company_data, logo_data) {
            // Delete attribute to avoid "Field_changed" errors
            removeUselessFields(company_data);

            // Assign VAT coming from parent VIES VAT query
            if(company.vat) company_data.vat = company.vat;
            def.resolve({
                company: company_data,
                logo: logo_data
            });
        });

        return def;
    },

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
}
});
