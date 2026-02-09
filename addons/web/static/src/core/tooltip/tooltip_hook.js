import { useLayoutEffect, useRef } from "@web/owl2/utils";
import { useService } from "@web/core/utils/hooks";


export function useTooltip(refName, params) {
    const tooltip = useService("tooltip");
    const ref = useRef(refName);
    useLayoutEffect(
        (el) => tooltip.add(el, params),
        () => [ref.el]
    );
}
