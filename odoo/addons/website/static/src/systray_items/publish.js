/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Switch } from '@website/components/switch/switch';
import { useService, useBus } from '@web/core/utils/hooks';
import { Component, xml, useState } from "@odoo/owl";

const websiteSystrayRegistry = registry.category('website_systray');

class PublishSystray extends Component {
    setup() {
        this.website = useService('website');
        this.rpc = useService('rpc');

        this.state = useState({
            published: this.website.currentWebsite.metadata.isPublished,
            processing: false,
        });

        useBus(websiteSystrayRegistry, 'CONTENT-UPDATED', () => this.state.published = this.website.currentWebsite.metadata.isPublished);
    }

    get label() {
        return this.state.published ? _t("Published") : _t("Unpublished");
    }

    /**
     * @todo event handlers should probably never return a Promise using OWL,
     * to adapt in master.
     */
    async publishContent() {
        if (this.state.processing) {
            return;
        }
        this.state.processing = true;
        this.state.published = !this.state.published;
        const { metadata: { mainObject } } = this.website.currentWebsite;
        return this.rpc('/website/publish', {
            id: mainObject.id,
            object: mainObject.model,
        }).then(
            published => {
                this.state.published = published;
                this.state.processing = false;
                return published;
            },
            err => {
                this.state.published = !this.state.published;
                this.state.processing = false;
                throw err;
            }
        );
    }
}
PublishSystray.template = xml`
<div t-on-click="publishContent" class="o_menu_systray_item o_publish_container d-md-flex ms-auto" data-hotkey="p" t-att-data-processing="state.processing and 1">
    <a href="#" class="o_nav_entry">
        <Switch value="state.published" disabled="true" extraClasses="'mb-0 o_switch_danger_success'"/>
        <span class="d-none d-md-block ms-1" t-esc="this.label"/>
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
