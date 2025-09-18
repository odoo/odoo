// @ts-check

/** @module @web/ui/tooltip/tooltip_hook - useTooltip hook to attach tooltips to OWL component refs */

import { useEffect, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
/**
 * @param {string} refName
 * @param {object} params
 */
export function useTooltip(refName, params) {
    const tooltip = useService("tooltip");
    const ref = useRef(refName);
    useEffect(
        (el) => tooltip.add(el, params),
        () => [ref.el],
    );
}
