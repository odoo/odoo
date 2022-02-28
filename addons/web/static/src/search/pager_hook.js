/** @odoo-module **/

const { useEnv, useChildSubEnv, useState, onWillRender } = owl;

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
    const pagerState = useState({});

    useChildSubEnv({
        config: {
            ...env.config,
            pagerProps: pagerState,
        },
    });
    onWillRender(() => {
        Object.assign(pagerState, getProps());
    });
}
