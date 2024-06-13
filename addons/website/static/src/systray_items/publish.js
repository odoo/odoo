/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { CheckBox } from '@web/core/checkbox/checkbox';
import { useService, useBus } from '@web/core/utils/hooks';
import { Component, xml, useState } from "@odoo/owl";

const websiteSystrayRegistry = registry.category('website_systray');

class PublishSystray extends Component {
    static template = xml`
        <div t-on-click="publishContent" class="o_menu_systray_item o_website_publish_container d-flex ms-auto" t-att-data-processing="state.processing and 1">
            <a href="#" class="d-flex align-items-center mx-1 px-2 px-md-0" data-hotkey="p">
                <span class="o_nav_entry d-none d-md-block mx-0 pe-1" t-esc="this.label"/>
                <CheckBox value="state.published" className="'form-switch d-flex justify-content-center m-0 pe-none'"/>
            </a>
        </div>`;
    static components = {
        CheckBox,
    };
    static props = {};

    setup() {
        this.website = useService('website');
        this.orm = useService('orm');

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
        return this.orm.call(
            mainObject.model,
            "website_publish_button",
            [[mainObject.id]],
        ).then(
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

export const systrayItem = {
    Component: PublishSystray,
    isDisplayed: env => env.services.website.currentWebsite && env.services.website.currentWebsite.metadata.canPublish,
};

websiteSystrayRegistry.add("Publish", systrayItem, { sequence: 12 });
