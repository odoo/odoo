/** @odoo-module **/

import { Wysiwyg } from "@web_editor/js/wysiwyg/wysiwyg";
import { useService } from '@web/core/utils/hooks';
import { patch } from "@web/core/utils/patch";

/**
 * The goal of this patch is to allow portal user to add images in html fields
 */
patch(Wysiwyg.prototype, {
    /**
     * @override
     */
    setup() {
        super.setup();
        this.http = useService('http');
    },
    /**
     * @overwrite
     */
    async _saveB64Image(el, resModel, resId) {
        if (resId) {
            el.classList.remove('o_b64_image_to_save');
            const params = {
                name: el.dataset.fileName || '',
                data: el.getAttribute('src').split('base64,')[1],
                res_id: resId,
                access_token: '',
                csrf_token: odoo.csrf_token,
            };

            const response = JSON.parse(await this.http.post('/project_sharing/attachment/add_image', params, "text"));
            if (response.error) {
                this.notification.add(response.error, { type: 'danger' });
                el.remove();
            }
            else {
                const attachment = response;
                let src = "/web/image/" + attachment.id + "-" + attachment.name;
                if (!attachment.public) {
                    let accessToken = attachment.access_token;
                    src += `?access_token=${encodeURIComponent(accessToken)}`;
                }
                el.setAttribute('src', src);
            }
        }
    },
});
