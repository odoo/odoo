/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { NewContentModal, MODULE_STATUS } from '@website/systray_items/new_content';
import { patch } from "@web/core/utils/patch";
import { xml } from "@odoo/owl";

patch(NewContentModal.prototype, {
    setup() {
        super.setup();

        this.state.newContentElements.push({
            moduleName: 'website_appointment',
            moduleXmlId: 'base.module_website_appointment',
            status: MODULE_STATUS.NOT_INSTALLED,
            icon: xml`<i class="fa fa-calendar"/>`,
            title: _t('Appointment Form'),
        });
    },
});
