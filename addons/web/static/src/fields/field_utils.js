// @ts-check

/** @module @web/fields/field_utils - Shared utilities for field extractProps and configuration */

/**
 * Extract digits precision from field attrs or options.
 *
 * The digits parameter is available as both an XML attribute (JSON string)
 * and a widget option (array). The attribute takes precedence.
 *
 * @param {{ attrs: Record<string, any>, options: Record<string, any> }} params
 * @returns {number[] | undefined}
 */
export function extractDigits({ attrs, options }) {
    if (attrs.digits) {
        return JSON.parse(attrs.digits);
    }
    if (options.digits) {
        return options.digits;
    }
    return undefined;
}

/**
 * Extract common numeric field props shared by float and integer fields.
 *
 * Covers formatting toggle, human-readable mode, input type, step size,
 * and decimal precision — the five props duplicated across both extractProps.
 *
 * @param {{ options: Record<string, any> }} params
 * @returns {{ formatNumber: boolean, humanReadable: boolean, inputType: string | undefined, step: number | undefined, decimals: number }}
 */
export function extractNumericOptions({ options }) {
    return {
        formatNumber:
            options?.enable_formatting !== undefined
                ? Boolean(options.enable_formatting)
                : true,
        humanReadable: !!options.human_readable,
        inputType: options.type,
        step: options.step,
        decimals: options.decimals || 0,
    };
}
