import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";


export class WebsiteSaleExtraInfoButton extends Interaction {
    static selector = "#form_extra_info";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _submitbutton: () => document.querySelector('[name="website_sale_main_button"]'),
    };
    dynamicContent = {
        _submitbutton: {"t-on-click": this.onSaveExtraInfo},
    };

    /**
     * @param {Event} ev
     */
    onSaveExtraInfo(ev) {
        const extraForm = this.el;
        const submitButton = ev.currentTarget;

        if (!ev.defaultPrevented && !submitButton.disabled) {
            ev.preventDefault();
            submitButton.disabled = true;
            const spinner = document.createElement('span');
            spinner.classList.add('fa', 'fa-cog', 'fa-spin');
            submitButton.appendChild(spinner);

            const inputEl = document.createElement("input");
            inputEl.setAttribute("type", "hidden");
            inputEl.setAttribute("name", "csrf_token");
            inputEl.setAttribute("value", odoo.csrf_token);
            this.insert(inputEl, extraForm);

            extraForm.submit();
        }
    }
}
registry
    .category("public.interactions")
    .add("website_sale.extra_info", WebsiteSaleExtraInfoButton);
