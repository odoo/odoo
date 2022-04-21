/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from '@web/core/utils/hooks';

const { Component, useState, useEffect } = owl;

class EditWebsiteSystray extends Component {
    setup(options = {}) {
        this.websiteService = useService('website');
        this.websiteContext = useState(this.websiteService.context);

        this.state = useState({
            isLoading: false,
        });

        useEffect((edition, snippetsLoaded) => {
            if (snippetsLoaded) {
                this.state.isLoading = false;
            }
            if (edition && !this.websiteService.wysiwygLoaded) {
                this.state.isLoading = true;
            }
        }, () => [this.websiteContext.edition, this.websiteContext.snippetsLoaded]);
    }

    startEdit() {
        this.websiteContext.edition = true;
    }
}
EditWebsiteSystray.template = "website.EditWebsiteSystray";

export const systrayItem = {
    Component: EditWebsiteSystray,
};

registry.category("website_systray").add("EditWebsite", systrayItem, { sequence: 9 });
