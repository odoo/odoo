/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from '@web/core/utils/hooks';

const { Component, useState, useEffect } = owl;

class EditWebsiteSystray extends Component {
    setup() {
        this.websiteService = useService('website');
        this.websiteContext = useState(this.websiteService.context);

        this.state = useState({
            isLoading: false,
        });

        useEffect((edition) => {
            if (edition) {
                this.state.isLoading = true;
            }
        }, () => [this.websiteContext.edition]);

        useEffect((snippetsLoaded) => {
            if (snippetsLoaded) {
                this.state.isLoading = false;
            }
        }, () => [this.websiteContext.snippetsLoaded]);
    }

    get translatable() {
        return this.websiteService.currentWebsite && this.websiteService.currentWebsite.metadata.translatable;
    }

    get label() {
        if (this.translatable) {
            return this.env._t("or edit master");
        }
        return this.env._t("Edit");
    }

    startEdit() {
        if (this.translatable) {
            // We are in translate mode, the pathname starts with '/<url_code>'. By
            // adding a trailing slash we can simply search for the first slash
            // after the language code to remove the language part.
            const { pathname, search, hash } = this.websiteService.contentWindow.location;
            const languagePrefix = `${pathname}/`.indexOf('/', 1);
            const defaultLanguagePathname = pathname.substring(languagePrefix);
            this.websiteService.goToWebsite({
                path: defaultLanguagePathname + search + hash,
                lang: 'default',
                edition: true
            });
        } else {
            this.websiteContext.edition = true;
        }
    }
}
EditWebsiteSystray.template = "website.EditWebsiteSystray";

export const systrayItem = {
    Component: EditWebsiteSystray,
    isDisplayed: (env) => env.services.website.isRestrictedEditor
        && env.services.website.currentWebsite.metadata.editable,
};

registry.category("website_systray").add("EditWebsite", systrayItem, { sequence: 7 });
