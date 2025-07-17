import { Interaction } from "@web/public/interaction";


export class WebsiteSaleExtraForm extends Interaction {
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _submitbutton: () => document.querySelector('[name="website_sale_main_button"]'),
    };
    dynamicContent = {
        _submitbutton: {"t-on-click": this.onSaveForm},
    };

    /**
     * @param {Event} ev
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

            // Adding the CSRF token here to keep the template editable from the website editor.
            const inputEl = document.createElement("input");
            inputEl.setAttribute("type", "hidden");
            inputEl.setAttribute("name", "csrf_token");
            inputEl.setAttribute("value", odoo.csrf_token);
            this.insert(inputEl, theForm);

            theForm.submit();
        }
    }
}
