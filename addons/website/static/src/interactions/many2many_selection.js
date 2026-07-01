import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class Many2ManySelection extends Interaction {
    static selector = ".s_website_form_m2m_selection";
    dynamicContent = {
        ".dropdown-item": { "t-on-click": this.onOptionClick },
        ".s_website_form_m2m_pill_remove": { "t-on-click.stop": this.onPillRemove },
    };

    setup() {
        this.selectEl = this.el.querySelector("select.s_website_form_input");
        this.pillsContainer = this.el.querySelector(".s_website_form_m2m_pills_container");
        this.placeholderEl = this.pillsContainer.querySelector(".s_website_form_m2m_placeholder");
        this.elements = new Map();
        const initiallySelectedOptions = new Map();
        for (const optionEl of this.selectEl.options) {
            const value = optionEl.value;
            const escaped = CSS.escape(value);
            this.elements.set(value, {
                optionEl,
                pillEl: this.pillsContainer.querySelector(
                    `.s_website_form_m2m_pill[data-value="${escaped}"]`
                ),
                itemEl: this.el.querySelector(`.dropdown-item[data-value="${escaped}"]`),
            });
            initiallySelectedOptions.set(value, optionEl.hasAttribute("selected"));
        }
        this.registerCleanup(() => {
            const dropdown = window.Dropdown.getInstance(
                this.pillsContainer.querySelector("button[data-bs-toggle='dropdown']")
            );
            dropdown?.hide();
            dropdown?.dispose();
            for (const [value, selected] of initiallySelectedOptions) {
                this.setSelection(value, selected);
            }
        });
    }

    /**
     * Applies the selection state for a given option value across the three
     * linked elements: the hidden `<select>` option, its pill, and its
     * dropdown-item's aria-checked state. Also refreshes the placeholder
     * visibility.
     *
     * @param {string} value option value to update.
     * @param {boolean} selected target selection state.
     */
    setSelection(value, selected) {
        const { optionEl, pillEl, itemEl } = this.elements.get(value);
        optionEl.selected = selected;
        pillEl?.classList.toggle("d-none", !selected);
        itemEl?.setAttribute("aria-checked", selected);
        if (selected && pillEl) {
            this.pillsContainer.appendChild(pillEl);
        }
        this.placeholderEl.classList.toggle("d-none", this.hasSelection());
    }

    /**
     * @returns {boolean} whether any option is currently selected.
     */
    hasSelection() {
        for (const { optionEl } of this.elements.values()) {
            if (optionEl.selected) {
                return true;
            }
        }
        return false;
    }

    onOptionClick(ev) {
        const value = ev.currentTarget.dataset.value;
        const { optionEl } = this.elements.get(value);
        this.setSelection(value, !optionEl.selected);
        this.selectEl.dispatchEvent(new Event("input", { bubbles: true }));
    }

    onPillRemove(ev) {
        const pillEl = ev.currentTarget.closest(".s_website_form_m2m_pill");
        this.setSelection(pillEl.dataset.value, false);
        this.selectEl.dispatchEvent(new Event("input", { bubbles: true }));
    }
}

registry.category("public.interactions").add("website.many2many_selection", Many2ManySelection);
