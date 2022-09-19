/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Switch } from '@website/components/switch/switch';
import { useService } from '@web/core/utils/hooks';

const { Component, xml, useState } = owl;

const websiteSystrayRegistry = registry.category('website_systray');

class PublishSystray extends Component {
    setup() {
        this.website = useService('website');
        this.rpc = useService('rpc');

        this.currentWebsite = useState(this.website.currentWebsite);
    }

    get label() {
        return this.currentWebsite.metadata.isPublished ? this.env._t("Published") : this.env._t("Unpublished");
    }

    publishContent() {
        this.website.currentWebsite.metadata.isPublished = !this.website.currentWebsite.metadata.isPublished;
        const { metadata: { mainObject } } = this.website.currentWebsite;
        return this.rpc('/website/publish', {
            id: mainObject.id,
            object: mainObject.model,
        });
    }
}
PublishSystray.template = xml`
<div t-on-click="publishContent" class="o_menu_systray_item d-md-flex ms-auto" data-hotkey="p">
    <a href="#">
        <Switch value="currentWebsite.metadata.isPublished" extraClasses="'mb-0 o_switch_danger_success'"/>
        <span class="d-none d-md-block ms-2" t-esc="this.label"/>
    </a>
</div>`;
PublishSystray.components = {
    Switch
};

export const systrayItem = {
    Component: PublishSystray,
    isDisplayed: env => env.services.website.currentWebsite.metadata.canPublish,
};

websiteSystrayRegistry.add("Publish", systrayItem, { sequence: 12 });
