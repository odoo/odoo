// @ts-check

/** @module @web/search/pager_hook - OWL hook that injects reactive pager props into the sub-environment */

import { onWillRender, useEnv, useState, useSubEnv } from "@odoo/owl";

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
