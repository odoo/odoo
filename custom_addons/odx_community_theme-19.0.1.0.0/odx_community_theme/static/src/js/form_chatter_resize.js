/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";
import { onMounted, onPatched, onWillUnmount } from "@odoo/owl";

/**
 * Injects a draggable resize handle between form sheet and side chatter.
 * Width persisted in localStorage.
 */
const STORAGE_KEY = "odx.chatter.width";
const MIN_WIDTH = 280;
const MAX_WIDTH_RATIO = 0.55;
const HANDLE_CLASS = "odx-chatter-resize-handle";

patch(FormRenderer.prototype, {
    setup() {
        super.setup();
        this._odxResizeHandles = [];

        const tryInject = () => {
            setTimeout(() => this._odxInjectResizeHandle(), 300);
        };
        onMounted(tryInject);
        onPatched(tryInject);
        onWillUnmount(() => {
            // Cleanup
            for (const handle of this._odxResizeHandles) {
                handle.remove();
            }
            this._odxResizeHandles = [];
        });
    },

    _odxInjectResizeHandle() {
        // Find the form renderer element in the DOM
        const renderers = document.querySelectorAll(".o_form_renderer");
        if (!renderers.length) return;

        for (const renderer of renderers) {
            // Skip if already injected
            if (renderer.querySelector(`.${HANDLE_CLASS}`)) continue;

            // Find the chatter — it's a sibling of .o_form_sheet_bg
            const sheetBg = renderer.querySelector(".o_form_sheet_bg");
            const chatter = renderer.querySelector(".o-mail-Form-chatter");
            if (!sheetBg || !chatter) continue;

            // Only for side-by-side layout (flex-row parent)
            const style = window.getComputedStyle(renderer);
            const isRow = style.flexDirection === "row"
                || style.flexWrap === "nowrap"
                || renderer.classList.contains("flex-nowrap");
            if (!isRow) continue;

            // Restore saved width
            const saved = localStorage.getItem(STORAGE_KEY);
            if (saved) {
                const w = parseInt(saved, 10);
                if (w >= MIN_WIDTH) {
                    chatter.style.width = `${w}px`;
                    chatter.style.flexBasis = `${w}px`;
                    chatter.style.flexGrow = "0";
                    chatter.style.flexShrink = "0";
                }
            }

            // Create and insert handle
            const handle = document.createElement("div");
            handle.className = HANDLE_CLASS;
            handle.title = "Drag to resize chatter";
            renderer.insertBefore(handle, chatter);
            this._odxResizeHandles.push(handle);

            // Drag events
            handle.addEventListener("mousedown", (e) => {
                e.preventDefault();
                const startX = e.clientX;
                const startW = chatter.offsetWidth;
                const maxW = renderer.offsetWidth * MAX_WIDTH_RATIO;

                document.body.style.cursor = "col-resize";
                document.body.style.userSelect = "none";
                handle.classList.add("odx-resizing");

                const onMove = (ev) => {
                    const delta = startX - ev.clientX;
                    const newW = Math.max(MIN_WIDTH, Math.min(maxW, startW + delta));
                    chatter.style.width = `${newW}px`;
                    chatter.style.flexBasis = `${newW}px`;
                    chatter.style.flexGrow = "0";
                    chatter.style.flexShrink = "0";
                };

                const onUp = () => {
                    document.removeEventListener("mousemove", onMove);
                    document.removeEventListener("mouseup", onUp);
                    document.body.style.cursor = "";
                    document.body.style.userSelect = "";
                    handle.classList.remove("odx-resizing");
                    localStorage.setItem(STORAGE_KEY, String(parseInt(chatter.style.width, 10)));
                };

                document.addEventListener("mousemove", onMove);
                document.addEventListener("mouseup", onUp);
            });
        }
    },
});
