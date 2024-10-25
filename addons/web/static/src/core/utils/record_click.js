import { useEffect, useRef } from "@odoo/owl";
import { isMacOS } from "@web/core/browser/feature_detection";

const EXCLUDED_TAGS = ["a", "button", "img"];
//FIXME must support debounce, I guess...
export function useRecordClick({ refName, onOpen, excludedSelectors = [] }) {
    const _excludedSelectors = [...EXCLUDED_TAGS, ...excludedSelectors];
    const ref = useRef(refName);
    const handleClick = (ev) => {
        if (!ev.target.classList.contains("middle_clickable")) {
            // keep the default browser behavior if the click on the element is not explicitly handled by the hook
            // case 1 when the hook must handle: <a> tag in an element middle clickable
            // case 2 when the hook must handle: <span> tag in a <button> element middle clickable
            if (ev.target.matches(_excludedSelectors)) {
                return;
            }
            const excludedParent = ev.target.closest(_excludedSelectors);
            if (excludedParent && !excludedParent.classList.contains("middle_clickable")) {
                return;
            }
        }
        const ctrlKey = isMacOS() ? ev.metaKey : ev.ctrlKey;
        const midlleClick = (ctrlKey && ev.button === 0) || ev.button === 1;
        if ([0, 1].includes(ev.button)) {
            onOpen(ev, midlleClick);
            ev.preventDefault();
            ev.stopPropagation();
        }
    };
    useEffect(
        () => {
            if (ref.el) {
                const el = ref.el;
                el.classList.add("middle_clickable");
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
