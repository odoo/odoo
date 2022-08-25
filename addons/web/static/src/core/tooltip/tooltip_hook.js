/** @odoo-module */

import { useService } from "@web/core/utils/hooks";

const { useEffect, useRef } = owl;

export function useTooltip(refName, params) {
    const tooltip = useService("tooltip");
    const ref = useRef(refName);
    useEffect(
        (el) => tooltip.add(el, params),
        () => [ref.el]
    );
}
