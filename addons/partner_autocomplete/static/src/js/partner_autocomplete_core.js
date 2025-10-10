/* global checkVATNumber */

import { loadJS } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";
import { KeepLast } from "@web/core/utils/concurrency";
import { useService } from "@web/core/utils/hooks";
import { renderToMarkup } from "@web/core/utils/render";
import { onWillStart } from "@odoo/owl";

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

    let lastNoResultsQuery = null;

    onWillStart(async () => {
        await loadJS("/partner_autocomplete/static/lib/jsvat.js");
    });

    function sanitizeVAT(value) {
        return value ? value.replace(/[^A-Za-z0-9]/g, '') : '';
    }

    async function isVATNumber(value) {
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
        return enrichCompany(company).then((companyData) => {
            // Fetch additional company info via Autocomplete Enrichment API

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
            return {
                company: companyData,
                logo: companyData.logo || false,
            };
        })
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

        // Optimization: if the search query starts with the same content as a previous query for
        // which there was no results, there won't be any results for the current query.
        // E.g., if there is no results for query "abc123", there won't be any results for query "abc1234".
        if (!isVAT && lastNoResultsQuery && value.startsWith(lastNoResultsQuery)) {
            return [];
        }

        const prom = orm.silent.call(
            'res.partner',
            method,
            [value, queryCountryId],
        );

        const suggestions = await keepLastOdoo.add(prom);

        if (!isVAT && suggestions.length === 0) {
            lastNoResultsQuery = value;
        }

        await Promise.all(suggestions.map(async (suggestion) => {
            suggestion.query = value;  // Save queried value (name, VAT) for later
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
