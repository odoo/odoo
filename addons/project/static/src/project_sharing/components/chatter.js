/** @odoo-module **/

import { PortalChatter } from 'portal.chatter';
import Composer from './composer';

export default PortalChatter.extend({
    _messageFetchPrepareParams() {
        const data = this._super.apply(this, arguments);
        if (this.options.project_sharing_id) {
            data.project_sharing_id = this.options.project_sharing_id;
        }
        return data;
    },
    _createComposerWidget() {
        return new Composer(this, this.options);
    },
});
