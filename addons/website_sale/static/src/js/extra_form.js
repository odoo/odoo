import { Interaction } from "@web/public/interaction";


export class WebsiteSaleFormButton extends Interaction {
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _submitbutton: () => document.querySelector('[name="website_sale_main_button"]'),
    };
    dynamicContent = {
        _submitbutton: {"t-on-click": this.onSaveForm},
    };

    /**
     * @param {Event} ev
     * TODO-PDA simpler version with _submitForm see payment_form.js
     */
    onSaveForm(ev) {
        const theForm = this.el;
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
            this.insert(inputEl, theForm);

            theForm.submit();
        }
    }
}
