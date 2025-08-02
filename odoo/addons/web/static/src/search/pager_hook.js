/** @odoo-module **/

import { useEnv, useSubEnv, useState, onWillRender } from "@odoo/owl";

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

    useSubEnv({
        config: {
            ...env.config,
            pagerProps: pagerState,
        },
    });
    onWillRender(() => {
        Object.assign(pagerState, getProps() || { total: 0 });
    });
}
