import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
// import { useService } from "@web/core/utils/hooks";


export class WebsiteSaleExtraInfo extends Interaction {
    static selector = "#class_extra_info";

    dynamicSelectors = {
        ...this.dynamicSelectors,
        _submitbutton: () => document.getElementsByName('website_sale_main_button')[0],
    };
    dynamicContent = {
        ...this.dynamicContent,
        _submitbutton: {
            "t-on-click": this._onSaveExtraInfo,
        },
    };

    // setup() {
    //     console.log("passing in setup")
    //     this.http = useService('http');
    // }

    async _onSaveExtraInfo(ev) {
        console.log("passing in _onSaveExtraInfo")
        const extraForm = document.querySelector('form.form_extra_info');

        if (!extraForm.reportValidity()) {
            return
        }
        const submitButton = ev.currentTarget;
        if (!ev.defaultPrevented && !submitButton.disabled) {
            ev.preventDefault();

            submitButton.disabled = true;
            const spinner = document.createElement('span');
            spinner.classList.add('fa', 'fa-cog', 'fa-spin');
            submitButton.appendChild(spinner);

            const formData = new FormData(extraForm);

            // Avoid sending empty files
            const emptyFileInputs = [...extraForm.querySelectorAll('input[type="file"]')]
            .filter(input => input.files.length === 0);
            emptyFileInputs.forEach(input => {
                formData.delete(input.name);
            });

            // const formObject = Object.fromEntries(formData.entries());
            // formObject.csrf_token = odoo.csrf_token;
            // console.log("formObject TOKEN: ", formObject.csrf_token)
            console.log("formData TOKEN: ", formData.get('csrf_token'))
            // console.log("formData entries: ", formData)
            // console.log("Form Data before sending:", Array.from(formData.entries()));

            // const result = await rpc( '/website/form/shop.sale.order', formObject);
            const result = await rpc('/website/form/shop.sale.order', formData);
            // const result = await this.http.post('/website/form/shop.sale.order', formData);

            console.log("result: ", result)
            // no errors
            if (result.id) {
                window.location = '/shop/confirm_order';
            } else {
                // Re-enable button and remove spinner
                submitButton.disabled = false;
                spinner.remove();
            }
        }
    }


}
registry
    .category("public.interactions")
    .add("website_sale.extra_info", WebsiteSaleExtraInfo);


// import publicWidget from "@web/legacy/js/public/public_widget";

// publicWidget.registry.websiteSaleExtraInfo = publicWidget.Widget.extend({
//     // /shop/extra_info
//     selector: '#class_extra_info',

//     /**
//      * @constructor
//      */
//     init: function () {
//         this._super.apply(this, arguments);

//         this.http = this.bindService('http');

//         this.submitButton =  document.getElementsByName('website_sale_main_button')[0]
//         this._boundSaveExtraInfo = this._onSaveExtraInfo.bind(this);
//         this.submitButton.addEventListener("click", this._boundSaveExtraInfo);
//         this.extraForm = document.querySelector('form.form_extra_info');
//     },

//     destroy() {
//         this.submitButton.removeEventListener("click", this._boundSaveExtraInfo);
//         this._super(...arguments);
//     },

//     //--------------------------------------------------------------------------
//     // Handlers
//     //--------------------------------------------------------------------------

//     /**
//      * Disable the button, submit the form and add a spinner while the submission is ongoing
//      *
//      * @private
//      * @param {Event} ev
//      */
//     async _onSaveExtraInfo(ev) {
//         if (!this.extraForm.reportValidity()) {
//             return
//         }
//         const submitButton = ev.currentTarget;
//         if (!ev.defaultPrevented && !submitButton.disabled) {
//             ev.preventDefault();

//             submitButton.disabled = true;
//             const spinner = document.createElement('span');
//             spinner.classList.add('fa', 'fa-cog', 'fa-spin');
//             submitButton.appendChild(spinner);

//             const formData = new FormData(this.extraForm);

//             const emptyFileInputs = [...this.extraForm.querySelectorAll('input[type="file"]')]
//             .filter(input => input.files.length === 0);

//             // Avoid sending empty files
//             emptyFileInputs.forEach(input => {
//                 formData.delete(input.name);
//             });

//             formData.append("csrf_token", odoo.csrf_token);
//             const result = await this.http.post(
//                 '/website/form/shop.sale.order',
//                 formData,
//             )
//             // no errors
//             if (result.id) {
//                 window.location = '/shop/confirm_order';
//             } else {
//                 // Re-enable button and remove spinner
//                 submitButton.disabled = false;
//                 spinner.remove();
//             }
//         }
//     },
// });

// export default publicWidget.registry.websiteSaleExtraInfo;
