/** @odoo-module **/

import {useService, useAutofocus} from '@web/core/utils/hooks';
import {WebsiteDialog} from './dialog';
const {Component, useState, onWillStart} = owl;

export class DuplicateObjectDialog extends Component {
    setup() {
        this.orm = useService('orm');
        this.website = useService('website');
        this.notification = useService('notification');
        this.rpc = useService('rpc');
        useAutofocus();
        this.title = this.env._t('Duplicate');
        this.state = useState({
            name: '',
        });
        onWillStart(this._updateModalTitle);
    }
    async duplicate() {
        if (!this.state.name) {
            this.notification.add(this.env._t('Please enter a name.'), {
                title: this.env._t('Attention'),
                type: 'warning',
            });
            return;
        }
        const mainObject = this.website.currentWebsite.metadata.mainObject;
        let url;
        if (mainObject.model === 'website.page') {
            url = await this.orm.call(
                mainObject.model,
                'clone_page',
                [mainObject.id, this.state.name],
            );
        } else {
            url = await this.rpc('/website/duplicate', {
                model: mainObject.model,
                object_id: mainObject.id,
                new_name: this.state.name,
            });
        }
        this.website.goToWebsite({path: url, edition: true});
        this.props.close();
        if (this.props.onDuplicate) {
            this.props.onDuplicate();
        }
    }
    async _updateModalTitle() {
        this.objectName = await this.website.getUserModelName();
    }
}
DuplicateObjectDialog.components = {WebsiteDialog};
DuplicateObjectDialog.template = 'website.DuplicateObjectDialog';
