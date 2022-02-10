/** @odoo-module **/

const { useEnv, useChildSubEnv } = owl;

/**
 * @typedef PagerUpdateParams
 * @property {number} offset
 * @property {number} limit
 */

/**
 * @typedef PagerProps
 * @property {number} offset
 * @property {number} limit
 * @property {number} total
 * @property {(params: PagerUpdateParams) => any} onUpdate
 * @property {boolean} [isEditable]
 * @property {boolean} [withAccessKey]
 */

/**
 * @param {() => PagerProps} getProps
 */
export function usePager(getProps) {
    const env = useEnv();

    useChildSubEnv({
        config: {
            ...env.config,
            getPagerProps: getProps,
        },
    });
}
