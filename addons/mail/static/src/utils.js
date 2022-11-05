/** @odoo-module */

import { onMounted, onPatched, onWillPatch, onWillUnmount, useRef } from "@odoo/owl";

export function removeFromArray(array, elem) {
    const index = array.indexOf(elem);
    if (index >= 0) {
        array.splice(index, 1);
    }
}

export function htmlToTextContentInline(htmlString) {
    const fragment = document.createDocumentFragment();
    const div = document.createElement("div");
    fragment.appendChild(div);
    htmlString = htmlString.replace(/<br\s*\/?>/gi, " ");
    try {
        div.innerHTML = htmlString;
    } catch (_e) {
        div.innerHTML = `<pre>${htmlString}</pre>`;
    }
    return div.textContent
        .trim()
        .replace(/[\n\r]/g, "")
        .replace(/\s\s+/g, " ");
}

export function onExternalClick(refName, cb) {
    const ref = useRef(refName);
    function onClick(ev) {
        if (ref.el && !ref.el.contains(ev.target)) {
            cb();
        }
    }
    onMounted(() => {
        document.body.addEventListener("click", onClick, true);
    });
    onWillUnmount(() => {
        document.body.removeEventListener("click", onClick, true);
    });
}

export function useAutoScroll(refName) {
    const ref = useRef(refName);
    let isScrolled = false;
    onMounted(() => {
        ref.el.scrollTop = ref.el.scrollHeight;
    });
    onWillPatch(() => {
        const el = ref.el;
        isScrolled = Math.abs(el.scrollTop + el.clientHeight - el.scrollHeight) < 1;
    });
    onPatched(() => {
        if (isScrolled) {
            ref.el.scrollTop = ref.el.scrollHeight;
        }
    });
}
