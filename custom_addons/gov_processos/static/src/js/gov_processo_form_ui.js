/** @odoo-module **/

import { onMounted, onPatched } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";

const GOV_CHATTER_COLLAPSED_KEY = "govProcessoChatterCollapsed";
const GOV_CHATTER_WIDTH_KEY = "govProcessoChatterWidth";
const MIN_CHATTER_WIDTH = 340;
const MAX_CHATTER_WIDTH = 1200;
const CHATTER_SELECTORS = [
    ".o-mail-Form-chatter",
    ".o_FormRenderer_chatterContainer",
    ".oe_chatter",
];

function getChatter(root) {
    for (const selector of CHATTER_SELECTORS) {
        const el = root.querySelector(selector);
        if (el) {
            return el;
        }
    }
    return null;
}

patch(FormRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        onMounted(() => this._govApplyProcessoFormUI());
        onPatched(() => this._govApplyProcessoFormUI());
    },

    _govApplyProcessoFormUI() {
        if (this.props.resModel !== "gov.processo" || !this.el) {
            return;
        }
        const root = this.el;
        if (window.innerWidth < 1280) {
            root.classList.remove("gov-chatter-enhanced", "gov-chatter-collapsed");
            const oldBtn = root.querySelector(".gov-proc-chatter-toggle");
            if (oldBtn) {
                oldBtn.remove();
            }
            return;
        }

        root.classList.add("gov-chatter-enhanced");
        const chatter = getChatter(root);
        if (!chatter) {
            return;
        }

        const savedWidth = parseInt(window.localStorage.getItem(GOV_CHATTER_WIDTH_KEY), 10);
        if (!Number.isNaN(savedWidth) && savedWidth >= MIN_CHATTER_WIDTH && savedWidth <= MAX_CHATTER_WIDTH) {
            chatter.style.width = `${savedWidth}px`;
        }

        if (!chatter.dataset.govResizeBound) {
            chatter.dataset.govResizeBound = "1";
            const persistWidth = () => {
                const width = Math.round(chatter.getBoundingClientRect().width);
                if (width >= MIN_CHATTER_WIDTH && width <= MAX_CHATTER_WIDTH) {
                    window.localStorage.setItem(GOV_CHATTER_WIDTH_KEY, String(width));
                }
            };
            chatter.addEventListener("mouseup", persistWidth);
            chatter.addEventListener("mouseleave", persistWidth);
        }

        let toggleButton = root.querySelector(".gov-proc-chatter-toggle");
        if (!toggleButton) {
            toggleButton = document.createElement("button");
            toggleButton.type = "button";
            toggleButton.className = "gov-proc-chatter-toggle";
            toggleButton.addEventListener("click", () => {
                const isCollapsed = root.classList.toggle("gov-chatter-collapsed");
                window.localStorage.setItem(GOV_CHATTER_COLLAPSED_KEY, isCollapsed ? "1" : "0");
                this._govSetToggleText(toggleButton, isCollapsed);
            });
            root.appendChild(toggleButton);
        }

        const collapsed = window.localStorage.getItem(GOV_CHATTER_COLLAPSED_KEY) === "1";
        root.classList.toggle("gov-chatter-collapsed", collapsed);
        this._govSetToggleText(toggleButton, collapsed);
    },

    _govSetToggleText(button, collapsed) {
        button.textContent = collapsed ? "Mostrar Registros" : "Ocultar Registros";
        button.title = collapsed
            ? "Mostrar barra lateral de registros"
            : "Ocultar barra lateral de registros";
    },
});
