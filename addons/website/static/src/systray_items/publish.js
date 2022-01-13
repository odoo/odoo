/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Switch } from '@website/components/switch/switch';
import { useService, useBus } from '@web/core/utils/hooks';

const { Component, xml, useState } = owl;

const websiteSystrayRegistry = registry.category('website_systray');

class PublishSystray extends Component {
    setup() {
        this.website = useService('website');
        this.rpc = useService('rpc');

        this.state = useState({
            published: this.website.currentWebsite.metadata.isPublished,
        });

        useBus(websiteSystrayRegistry, 'CONTENT-UPDATED', () => this.state.published = this.website.currentWebsite.metadata.isPublished);
    }

    publishContent() {
        this.state.published = !this.state.published;
        const { metadata: { id, object } } = this.website.currentWebsite;
        return this.rpc('/website/publish', {
            id,
            object,
        });
    }
}
PublishSystray.template = xml`
<div t-on-click="publishContent" class="o_menu_systray_item d-md-flex ml-auto">
    <a href="#">
        <Switch value="state.published" extraClasses="'mb-0 o_switch_danger_success'"/>
        <t t-esc="state.published? 'Published' : 'Unpublished'"/>
    </a>
</div>`;
PublishSystray.components = {
    Switch
};

export const systrayItem = {
    Component: PublishSystray,
    isDisplayed: env => env.services.website.currentWebsite && env.services.website.currentWebsite.metadata.canPublish,
};

websiteSystrayRegistry.add("Publish", systrayItem, { sequence: 12 });
