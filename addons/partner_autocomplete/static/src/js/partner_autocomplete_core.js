/** @odoo-module **/
/* global checkVATNumber */

import { loadJS } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";
import { KeepLast } from "@web/core/utils/concurrency";
import { useService } from "@web/core/utils/hooks";
import { renderToMarkup } from "@web/core/utils/render";
import { getDataURLFromFile } from "@web/core/utils/urls";

/**
 * Get list of companies via Autocomplete API
 *
 * @param {string} value
 * @returns {Promise}
 * @private
 */
export function usePartnerAutocomplete() {
    const keepLastOdoo = new KeepLast();
    const keepLastClearbit = new KeepLast();

    const http = useService("http");
    const notification = useService("notification");
    const orm = useService("orm");

    function sanitizeVAT(value) {
        return value ? value.replace(/[^A-Za-z0-9]/g, '') : '';
    }

    async function isVATNumber(value) {
        // Lazyload jsvat only if the component is being used.
        await loadJS("/partner_autocomplete/static/lib/jsvat.js");

        // checkVATNumber is defined in library jsvat.
        // It validates that the input has a valid VAT number format
        return checkVATNumber(sanitizeVAT(value));
    }

    async function checkGSTNumber(value) {
        // Lazyload jsvat only if the component is being used.
        // Check if the input is a valid GST number.
        let isGST = false;
        if (value && value.length === 15) {
            const allGSTinRe = [
                /\d{2}[a-zA-Z]{5}\d{4}[a-zA-Z][1-9A-Za-z][Zz1-9A-Ja-j][0-9a-zA-Z]/, // Normal, Composite, Casual GSTIN
                /\d{4}[A-Z]{3}\d{5}[UO]N[A-Z0-9]/, // UN/ON Body GSTIN
                /\d{4}[a-zA-Z]{3}\d{5}NR[0-9a-zA-Z]/, // NRI GSTIN
                /\d{2}[a-zA-Z]{4}[a-zA-Z0-9]\d{4}[a-zA-Z][1-9A-Za-z][DK][0-9a-zA-Z]/, // TDS GSTIN
                /\d{2}[a-zA-Z]{5}\d{4}[a-zA-Z][1-9A-Za-z]C[0-9a-zA-Z]/ // TCS GSTIN
            ];

            isGST = allGSTinRe.some((re) => re.test(value));
        }

        return isGST;
    }

    async function autocomplete(value) {
        value = value.trim();

        const isVAT = await isVATNumber(value) || await checkGSTNumber(value);
        let odooSuggestions = [];
        let clearbitSuggestions = [];
        return new Promise((resolve, reject) => {
            const odooPromise = getOdooSuggestions(value, isVAT).then((suggestions) => {
                odooSuggestions = suggestions;
            });

            // Only get Clearbit suggestions if not a VAT number
            const clearbitPromise = isVAT ? false : getClearbitSuggestions(value).then((suggestions) => {
                suggestions.forEach((suggestion) => {
                    suggestion.label = suggestion.name;
                    suggestion.website = suggestion.domain;
                    suggestion.description = suggestion.website;
                });
                clearbitSuggestions = suggestions;
            });

            const concatResults = () => {
                // Add Clearbit result with Odoo result (with unique domain)
                if (clearbitSuggestions && clearbitSuggestions.length) {
                    const websites = odooSuggestions.map((suggestion) => {
                        return suggestion.website;
                    });
                    clearbitSuggestions.forEach((suggestion) => {
                        if (websites.indexOf(suggestion.domain) < 0) {
                            websites.push(suggestion.domain);
                            odooSuggestions.push(suggestion);
                        }
                    });
                }

                odooSuggestions = odooSuggestions.filter((suggestion) => {
                    return !suggestion.ignored;
                });
                odooSuggestions.forEach((suggestion) => {
                    delete suggestion.ignored;
                });
                return resolve(odooSuggestions);
            };

            whenAll([odooPromise, clearbitPromise]).then(concatResults, concatResults);
        });
    }

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
    function enrichCompany(company) {
        return orm.call(
            'res.partner',
            'enrich_company',
            [company.website, company.partner_gid, company.vat]
        );
    }

    /**
     * Get the company logo as Base 64 image from url
     *
     * @param {string} url
     * @returns {Promise}
     * @private
     */
    async function getCompanyLogo(url) {
        try {
            const base64Image = await getBase64Image(url)
            // base64Image equals "data:" if image not available on given url
            return base64Image ? base64Image.replace(/^data:image[^;]*;base64,?/, '') : false;
        }
        catch {
            return false;
        }
    }

    /**
     * Get enriched data + logo before populating partner form
     *
     * @param {Object} company
     * @returns {Promise}
     */
    function getCreateData(company) {
        const removeUselessFields = (company) => {
            // Delete attribute to avoid "Field_changed" errors
            const fields = ['label', 'description', 'domain', 'logo', 'legal_name', 'ignored', 'email', 'bank_ids', 'classList'];
            fields.forEach((field) => {
                delete company[field];
            });

            // Remove if empty and format it otherwise
            const many2oneFields = ['country_id', 'state_id'];
            many2oneFields.forEach((field) => {
                if (!company[field]) {
                    delete company[field];
                }
            });
        };

        return new Promise((resolve) => {
            // Fetch additional company info via Autocomplete Enrichment API
            const enrichPromise = enrichCompany(company);

            // Get logo
            const logoPromise = company.logo ? getCompanyLogo(company.logo) : false;
            whenAll([enrichPromise, logoPromise]).then(([company_data, logo_data]) => {
                // The vat should be returned for free. This is the reason why
                // we add it into the data of 'company' even if an error such as
                // an insufficient credit error is raised.
                if (company_data.error && company_data.vat) {
                    company.vat = company_data.vat;
                }

                if (company_data.error) {
                    if (company_data.error_message === 'Insufficient Credit') {
                        notifyNoCredits();
                    }
                    else if (company_data.error_message === 'No Account Token') {
                        notifyAccountToken();
                    }
                    else {
                        notification.add(company_data.error_message);
                    }
                    company_data = company;
                }

                if (!Object.keys(company_data).length) {
                    company_data = company;
                }

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
    }

    /**
     * Returns a promise which will be resolved with the base64 data of the
     * image fetched from the given url.
     *
     * @private
     * @param {string} url : the url where to find the image to fetch
     * @returns {Promise}
     */
    function getBase64Image(url) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.onload = () => {
                getDataURLFromFile(xhr.response).then(resolve);
            };
            xhr.open('GET', url);
            xhr.responseType = 'blob';
            xhr.onerror = reject;
            xhr.send();
        });
    }

    /**
     * Use Clearbit Autocomplete API to return suggestions
     *
     * @param {string} value
     * @returns {Promise}
     * @private
     */
    async function getClearbitSuggestions(value) {
        const url = `https://autocomplete.clearbit.com/v1/companies/suggest?query=${value}`;
        const prom = http.get(url);
        return keepLastClearbit.add(prom);
    }

    /**
     * Use Odoo Autocomplete API to return suggestions
     *
     * @param {string} value
     * @param {boolean} isVAT
     * @returns {Promise}
     * @private
     */
    async function getOdooSuggestions(value, isVAT) {
        const method = isVAT ? 'read_by_vat' : 'autocomplete';

        const prom = orm.silent.call(
            'res.partner',
            method,
            [value],
        );

        const suggestions = await keepLastOdoo.add(prom);
        suggestions.map((suggestion) => {
            suggestion.logo = suggestion.logo || '';
            suggestion.label = suggestion.legal_name || suggestion.name;
            if (suggestion.vat) suggestion.description = suggestion.vat;
            else if (suggestion.website) suggestion.description = suggestion.website;

            if (suggestion.country_id && suggestion.country_id.display_name) {
                if (suggestion.description) suggestion.description += ` (${suggestion.country_id.display_name})`;
                else suggestion.description += suggestion.country_id.display_name;
            }

            return suggestion;
        });
        return suggestions;
    }

    /**
     * Utility to wait for multiple promises
     * Promise.all will reject all promises whenever a promise is rejected
     * This utility will continue
     *
     * @param {Promise[]} promises
     * @returns {Promise}
     * @private
     */
    function whenAll(promises) {
        return Promise.all(promises.map((p) => {
            return Promise.resolve(p);
        }));
    }

    /**
     * @private
     * @returns {Promise}
     */
    async function notifyNoCredits() {
        const url = await orm.call(
            'iap.account',
            'get_credits_url',
            ['partner_autocomplete'],
        );
        const title = _t('Not enough credits for Partner Autocomplete');
        const content = renderToMarkup('partner_autocomplete.InsufficientCreditNotification', {
            credits_url: url
        });
        notification.add(content, {
            title,
        });
    }

    async function notifyAccountToken() {
        const url = await orm.call(
            'iap.account',
            'get_config_account_url',
            []
        );
        const title = _t('IAP Account Token missing');
        if (url) {
            const content = renderToMarkup('partner_autocomplete.AccountTokenMissingNotification', {
                account_url: url
            });
            notification.add(content, {
                title,
            });
        }
        else {
            notification.add(title);
        }
    }
    return { autocomplete, getCreateData, isVATNumber };
}
