import { useEffect, useRef } from "@odoo/owl";
import { isMacOS } from "@web/core/browser/feature_detection";

export function useRecordClick({ refName, onOpen, excludedSelectors = [], selector }) {
    const ref = useRef(refName);
    const handleClick = (ev) => {
        const _excludedSelector = excludedSelectors.join(",");
        if (_excludedSelector && ev.target.matches(_excludedSelector)) {
            return;
        }
        const ctrlKey = isMacOS() ? ev.metaKey : ev.ctrlKey;
        const middleClick = (ctrlKey && ev.button === 0) || ev.button === 1;
        if ([0, 1].includes(ev.button)) {
            const node = selector ? ev.target.closest(selector) : ev.currentTarget;
            if (node) {
                onOpen({ ev, middleClick, node });
                ev.preventDefault();
                ev.stopPropagation();
            }
        }
    };
    useEffect(
        () => {
            if (ref.el) {
                const el = ref.el;
                el.addEventListener("auxclick", handleClick);
                el.addEventListener("click", handleClick);
                return () => {
                    el.removeEventListener("auxclick", handleClick);
                    el.removeEventListener("click", handleClick);
                };
            }
        },
        () => [ref.el]
    );
}
