/** @odoo-module **/
/* global checkVATNumber */

import { loadJS } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
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

    function isGSTNumber(value) {
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

    async function autocomplete(value, queryCountryId) {
        value = value.trim();
        const isVAT = await isVATNumber(value);
        if (isVAT){
            value = sanitizeVAT(value);
        }
        const isGST = isGSTNumber(value);
        return await getSuggestions(value, isVAT || isGST, queryCountryId);
    }

    /**
     * Get enrichment data
     *
     * @param {Object} company
     * @returns {Promise}
     * @private
     */
    function enrichCompany(company) {
        if (isGSTNumber(company.query)){
            return orm.call('res.partner', 'enrich_by_gst', [company.query]);
        }
        return orm.call('res.partner', 'enrich_by_duns', [company.duns]);
    }

    function removeUselessFields(company, fieldsToKeep) {
        // Delete attribute to avoid "Field_changed" errors (these fields will be populated in the form)
        for (const field in company){
            if (!fieldsToKeep.includes(field)){
                delete company[field]
            }
        }
        return company;
    };

    /**
     * Get enriched data + logo before populating partner form
     *
     * @param {Object} company
     * @returns {Promise}
     */
    function getCreateData(company, fieldsToKeep) {
        return new Promise((resolve) => {
            // Fetch additional company info via Autocomplete Enrichment API
            const enrichPromise = enrichCompany(company);

            // Get logo
            const logoPromise = company.logoUrl ? getCompanyLogo(company.logoUrl) : false;
            whenAll([enrichPromise, logoPromise]).then(([companyData, logoData]) => {

                if (companyData.error) {
                    if (companyData.error_message === 'Insufficient Credit') {
                        notifyNoCredits();
                    }
                    else if (companyData.error_message === 'No Account Token') {
                        notifyAccountToken();
                    }
                    else {
                        notification.add(companyData.error_message);
                    }
                    companyData = {
                        ...company,
                        ...companyData,
                    };
                }

                resolve({
                    company: companyData,
                    logo: logoData
                });
            })
        });
    }

    async function fetchNoCaching(url) {
        try {
            const response = await browser.fetch(
                url,
                {
                    method: 'GET',
                    cache: 'no-cache',
                }
            );
            return await response.json();
        } catch {
            return {}
        }
    }

    /**
     * Use Clearbit API to get the company logo if there is a match with the company name or domain
     *
     * @param {string} value
     * @returns {Promise}
     * @private
     */
    async function getClearbitLogoUrl(company) {
        let clearbitData = await fetchNoCaching(encodeURI(`https://autocomplete.clearbit.com/v1/companies/suggest?query=${company.name}`));
        if (!clearbitData.length) {
            if (company.domain) {
                clearbitData = await fetchNoCaching(encodeURI(`https://autocomplete.clearbit.com/v1/companies/suggest?query=${company.domain}`));
            }
            if (!clearbitData.length) {
                return '';
            }
        }
        const firstResult = clearbitData[0];
        if (
            firstResult.name.toLowerCase() === company.name.toLowerCase()
            ||
            (
                company.domain !== undefined
                &&
                firstResult.domain === company.domain
            )
        ){
            return firstResult.logo;
        }
        return '';
    }

    /**
     * Get the company logo as Base 64 image from url
     *
     * @param {string} url
     * @returns {Promise}
     * @private
     */
    async function getCompanyLogo(logoUrl) {
        try {
            if (!logoUrl) {
                return false;
            }
            const base64Image = await getBase64Image(logoUrl);
            // base64Image equals "data:" if image not available on given url
            return base64Image ? base64Image.replace(/^data:image[^;]*;base64,?/, '') : false;
        }
        catch {
            return false;
        }
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
     * Use Odoo Autocomplete API to return suggestions
     *
     * @param {string} value
     * @param {boolean} isVAT
     * @returns {Promise}
     * @private
     */
    async function getSuggestions(value, isVAT, queryCountryId) {
        const method = isVAT ? 'autocomplete_by_vat' : 'autocomplete_by_name';

        const prom = orm.silent.call(
            'res.partner',
            method,
            [value, queryCountryId],
        );

        const suggestions = await keepLastOdoo.add(prom);
        await Promise.all(suggestions.map(async (suggestion) => {
            suggestion.query = value;  // Save queried value (name, VAT) for later
            suggestion.logoUrl = await getClearbitLogoUrl(suggestion);
            suggestion.description = '';
            if (suggestion.city){
                suggestion.description += suggestion.city;
            }
            // Show country name only if searching worldwide
            if (queryCountryId === 0 && suggestion.country_id && suggestion.country_id.display_name) {
                suggestion.description +=  ', ' + suggestion.country_id.display_name;
            }
            return suggestion;
        }));
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
    return { autocomplete, getCreateData, removeUselessFields };
}
