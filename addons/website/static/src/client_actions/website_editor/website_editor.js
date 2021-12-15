/** @odoo-module **/

import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';

const { Component, onWillStart } = owl;

export class WebsiteEditorClientAction extends Component {
    setup() {
        super.setup(...arguments);
        this.websiteService = useService('website');

        onWillStart(async () => {
            await this.websiteService.fetchWebsites();
            this.initialUrl = await this.websiteService.sendRequest(`/website/force/${this.websiteId}`, { path: this.path });
        });
    }

    get websiteId() {
        let websiteId = this.props.action.context.params && this.props.action.context.params.website_id;
        if (!websiteId) {
            websiteId = this.websiteService.websites[0].id;
        }
        return websiteId;
    }

    get path() {
        let path = this.props.action.context.params && this.props.action.context.params.path;
        if (!path) {
            path = '/';
        }
        return path;
    }
}
WebsiteEditorClientAction.template = 'website.WebsiteEditorClientAction';

registry.category('actions').add('website_editor', WebsiteEditorClientAction);
