/** @odoo-module **/

import { PortalComposer } from 'portal.composer';

export default PortalComposer.extend({
    _prepareAttachmentData() {
        const data = this._super.apply(this, arguments);
        const newData = {};
        if (this.options.display_composer && typeof this.options.display_composer == 'string') {
            // then we should have the access_token of the task
            newData.access_token = this.options.display_composer;
        } else {
            newData.project_sharing_id = this.options.project_sharing_id;
        }
        return Object.assign(data, newData);
    },
});
