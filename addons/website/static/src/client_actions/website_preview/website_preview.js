/** @odoo-module **/

import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';

const { Component, onWillStart } = owl;

export class WebsitePreview extends Component {
    setup() {
        this.websiteService = useService('website');

        onWillStart(async () => {
            await this.websiteService.fetchWebsites();
            const encodedPath = encodeURIComponent(this.path);
            this.initialUrl = `/website/force/${this.websiteId}?path=${encodedPath}`;
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
WebsitePreview.template = 'website.WebsitePreview';

registry.category('actions').add('website_preview', WebsitePreview);
