import { useLayoutEffect } from "@web/owl2/utils";
import { useService } from "@web/core/utils/hooks";

import { useRef } from "@odoo/owl";

export function useTooltip(refName, params) {
    const tooltip = useService("tooltip");
    const ref = useRef(refName);
    useLayoutEffect(
        (el) => tooltip.add(el, params),
        () => [ref.el]
    );
}
