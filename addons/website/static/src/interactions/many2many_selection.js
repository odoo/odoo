import { usePlugin } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { BootstrapInstance } from "@web/core/utils/bootstrap_plugin";
import { Interaction } from "@web/public/interaction";

export class Many2ManySelection extends Interaction {
    static selector = ".s_website_form_m2m_selection";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _form: () => this.el.closest("form"),
    };
    dynamicContent = {
        ".dropdown-item[data-value]": {
            "t-on-click": this.onOptionClick,
            "t-att-aria-checked": (el) => String(this.isSelected(el.dataset.value)),
        },
        ".s_website_form_m2m_pill": {
            "t-att-class": (el) => ({ "d-none": !this.isSelected(el.dataset.value) }),
        },
        ".s_website_form_m2m_pill_remove": { "t-on-click.stop": this.onPillRemove },
        ".s_website_form_m2m_placeholder": {
            "t-att-class": () => ({ "d-none": this.hasSelection() }),
        },
        ".s_website_form_m2m_remove_all": {
            "t-on-click.stop": () => this.setAll(false),
            "t-att-class": () => ({ "d-none": !this.hasSelection() }),
        },
        ".s_website_form_m2m_select_all": {
            "t-on-click": () => this.setAll(!this.isAllSelected()),
            "t-att-aria-checked": () => String(this.isAllSelected()),
            "t-out": () => (this.isAllSelected() ? _t("Deselect all") : _t("Select all")),
        },
        _form: { "t-on-reset": this.restoreInitialSelection },
    };

    setup() {
        this.bootstrap = usePlugin(BootstrapInstance);
        this.selectEl = this.el.querySelector("select.s_website_form_input");
        this.options = new Map(
            [...this.selectEl.options]
                .filter((optionEl) => !optionEl.classList.contains("s_website_form_empty_option"))
                .map((optionEl) => [optionEl.value, optionEl])
        );
        this.registerCleanup(() => {
            this.bootstrap
                .getInstance(window.Dropdown, this.el.querySelector("[data-bs-toggle='dropdown']"))
                ?.hide();
            this.restoreInitialSelection();
        });
    }

    restoreInitialSelection() {
        for (const optionEl of this.options.values()) {
            optionEl.selected = optionEl.defaultSelected;
        }
    }

    /**
     * @param {string} value option value
     * @returns {boolean} whether the option is currently selected.
     */
    isSelected(value) {
        return !!this.options.get(value)?.selected;
    }

    /**
     * The empty option is never selected, so the selected options are exactly
     * the selected records.
     *
     * @returns {boolean} whether at least one option is currently selected.
     */
    hasSelection() {
        return this.selectEl.selectedOptions.length > 0;
    }

    /**
     * @returns {boolean} whether every option is currently selected.
     */
    isAllSelected() {
        return this.options.size > 0 && this.selectEl.selectedOptions.length === this.options.size;
    }

    notifyChange() {
        this.selectEl.dispatchEvent(new Event("input", { bubbles: true }));
    }

    setAll(selected) {
        for (const optionEl of this.options.values()) {
            optionEl.selected = selected;
        }
        this.notifyChange();
    }

    onOptionClick(ev) {
        const optionEl = this.options.get(ev.currentTarget.dataset.value);
        optionEl.selected = !optionEl.selected;
        this.notifyChange();
    }

    onPillRemove(ev) {
        const value = ev.currentTarget.closest(".s_website_form_m2m_pill").dataset.value;
        this.options.get(value).selected = false;
        this.notifyChange();
    }
}

registry.category("public.interactions").add("website.many2many_selection", Many2ManySelection);
