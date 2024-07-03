/** @odoo-module **/

import PaymentPostProcessing from '@payment/js/post_processing';
import { renderToElement } from '@web/core/utils/render';


PaymentPostProcessing.include({
    _renderTemplate(xmlid, display_values={}) {
        if (this.getParent() && this.getParent().env && this.getParent().env.services && this.getParent().env.services.ui.isBlocked){
            this.call('ui', 'unblock');
        };
        const statusContainer = document.querySelector('div[name="o_payment_status_content"]');
        statusContainer.innerHTML = renderToElement(xmlid, display_values).innerHTML;
    },
})
