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
        this.rpc = useService('rpc');
        this.orm = useService('orm');

        this.websiteSelection = odoo.debug ? [{id: 0, name: this.env._t("All Websites")}] : [];

        this.state = useState({
            activeWebsite: undefined,
        });

        onWillStart(async () => {
            // `fetchWebsites()` already done by parent PageSearchModel
            this.websiteSelection.push(...this.website.websites);
            this.state.activeWebsite = await this.env.searchModel.getCurrentWebsite();
        });
    }

    /**
     * Adds the new 'website content' record depending on the targeted model and
     * 'create_action' passed in context.
     */
    async createWebsiteContent() {
        if (this.props.resModel === 'website.page') {
            return this.dialog.add(AddPageDialog, {selectWebsite: true});
        }
        const action = this.props.context.create_action;
        if (action) {
            if (/^\//.test(action)) {
                const url = await this.rpc(action);
                this.website.goToWebsite({ path: url, edition: true });
                return;
            }
            this.actionService.doAction(action, {
                onClose: (infos) => {
                    if (infos) {
                        this.website.goToWebsite({ path: infos.path });
                    }
                },
                props: {
                    onSave: (record, params) => {
                        if (record.resId && params.computePath) {
                            const path = params.computePath();
                            this.actionService.doAction({
                                type: "ir.actions.act_window_close",
                                infos: { path }
                            });
                        }
                    }
                }
            });
        }
    }

    onSelectWebsite(website) {
        this.state.activeWebsite = website;
        this.env.searchModel.notifyWebsiteChange(website.id);
    }
};

// TODO: Remove in master, records are not hidden through `t-if` anymore.
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
        const websiteId = record.data.website_id && record.data.website_id[0];
        return !this.props.activeWebsite.id
            || this.props.activeWebsite.id === websiteId
            || !websiteId && records.filter(rec => rec.data.website_url === record.data.website_url).length === 1;
    }
};
