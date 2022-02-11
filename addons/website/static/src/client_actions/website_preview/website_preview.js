/** @odoo-module **/

import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';

const { Component, onWillStart, useEffect, useRef } = owl;

export class WebsitePreview extends Component {
    setup() {
        this.websiteService = useService('website');

        this.iframe = useRef('iframe');

        onWillStart(async () => {
            await this.websiteService.fetchWebsites();
            const encodedPath = encodeURIComponent(this.path);
            this.initialUrl = `/website/force/${this.websiteId}?path=${encodedPath}`;
        });

        useEffect(() => {
            this.iframe.el.addEventListener('load', () => {
                // This replaces the browser url (/web#action=website...) with
                // the iframe's url (it is clearer for the user).
                this.currentUrl = this.iframe.el.contentDocument.location.href;
                history.replaceState({}, this.props.action.display_name, this.currentUrl);
            });
        }, () => []);
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
