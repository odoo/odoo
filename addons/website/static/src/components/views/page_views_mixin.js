/** @odoo-module **/

import {AddPageDialog} from "../dialog/dialog";
import {useService} from "@web/core/utils/hooks";

const {onWillStart, useState} = owl;

/**
 * Used to share code and keep the same behaviour on different types of 'website
 * content' views:
 * - Trigger the 'new content' dialogs when 'CREATE' button is clicked.
 * - Add a website selector on ControlPanel (that will be used by the renderer
 * to filter content).
 */
export const PageControllerMixin = (component) => class extends component {
    /**
     * @override
     */
    setup() {
        super.setup();
        this.website = useService('website');
        this.dialog = useService('dialog');

        this.websiteSelection = [{id: 0, name: this.env._t("All Websites")}];

        this.state = useState({
            activeWebsite: this.websiteSelection[0],
        });

        onWillStart(async () => {
            await this.website.fetchWebsites();
            this.websiteSelection.push(...this.website.websites);
        });
    }

    /**
     * Adds the new 'website content' record depending on the targeted model and
     * 'create_action' passed in context.
     */
    createWebsiteContent() {
        if (this.props.resModel === 'website.page') {
            return this.dialog.add(AddPageDialog, {selectWebsite: true});
        }
        const action = this.props.context.create_action;
        if (action) {
            if (/^\//.test(action)) {
                window.location.replace(action);
                return;
            }
            this.actionService.doAction(action, {
                onClose: (data) => {
                    if (data) {
                        this.website.goToWebsite({path: data.path});
                    }
                },
            });
        }
    }

    onSelectWebsite(website) {
        this.state.activeWebsite = website;
    }
};

export const PageRendererMixin = (component) => class extends component {
    /**
     * The goal here is to tweak the renderer to display records following some
     * rules:
     * - All websites (props.activeWebsite.id === 0):
     *     -> Show all generic/specific records.
     * - A website is selected:
     *     -> Display website-specific records & generic ones (only those without
     *        specific clones).
     */
    recordFilter(record, records) {
        return !this.props.activeWebsite.id
            || this.props.activeWebsite.id === record.data.website_id[0]
            || !record.data.website_id[0] && records.filter(rec => rec.data.website_url === record.data.website_url).length === 1;
    }
};
