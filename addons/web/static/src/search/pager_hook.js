import { onWillRender, useEnv, useState, useSubEnv } from "@web/owl2/utils";
import { untrack } from "@odoo/owl";

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
        untrack(() => {
            Object.assign(pagerState, getProps() || { total: 0 });
        });
    });
}
