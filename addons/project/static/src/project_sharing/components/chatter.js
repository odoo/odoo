/** @odoo-module **/

import { PortalChatter } from 'portal.chatter';
import Composer from './composer';

export default PortalChatter.extend({
    messageFetch(domain) {
        if (!this.options.res_id) {
            return Promise.resolve();
        }
        return this._super.apply(this, arguments);
    },
    _chatterInit() {
        if (!this.options.res_id) {
            this.result = { messages: [] };
            return Promise.resolve();
        }
        return this._super.apply(this, arguments);
    },
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
    update(props) {
        this._setOptions(props);
        this._reloadChatterContent();
    },
});
