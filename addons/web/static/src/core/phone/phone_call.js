import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

/**
 * @typedef {Object} PhoneCallParams
 * @property {string} phoneNumber
 * @property {string} [resModel]
 * @property {number} [resId]
 * @property {Object} [activity]
 */

export const phoneCallHandlerRegistry = registry.category("phone_call_handlers");

/** @param {string} phoneNumber */
export function getPhoneHref(phoneNumber) {
    return `tel:${phoneNumber.replace(/\s+/g, "")}`;
}

/**
 * @param {string} phoneNumber
 */
export function openPhoneLink(phoneNumber) {
    browser.open(getPhoneHref(phoneNumber));
}

/**
 * @param {import("@web/env").OdooEnv} env
 * @param {PhoneCallParams} params
 * @param {MouseEvent} [ev] A potential (click) event on the related `tel:`
 *      link: in that case we always prevent it to handle it ourselves. It could
 *      be nicer to not prevent it when not needed (e.g. when we don't have any
 *      phone handler defined) but it is unfortunately already prevented in
 *      some caller cases (e.g. phone field mobile DropdownItem).
 * @returns {boolean | Promise<boolean>} Whether a call was initiated.
 */
export function callPhoneNumber(env, params, ev) {
    ev?.preventDefault();
    const handler = phoneCallHandlerRegistry
        .getAll()
        .find((handler) => !handler.isApplicable || handler.isApplicable(env, params));
    const fallback = () => {
        openPhoneLink(params.phoneNumber);
        return true;
    };
    if (!handler) {
        return fallback();
    }
    return handler.execute(env, params, { fallback });
}
