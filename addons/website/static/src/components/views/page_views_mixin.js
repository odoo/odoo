/** @odoo-module **/

import {AddPageDialog} from "../dialog/dialog";
import {useService} from "@web/core/utils/hooks";

const { onWillStart, useEffect, useState } = owl;

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
        this.orm = useService("orm");

        this.websiteSelection = odoo.debug ? [{id: 0, name: this.env._t("All Websites")}] : [];

        this.state = useState({
            activeWebsite: undefined,
            firstLoad: true,
        });

        onWillStart(async () => {
            await this.website.fetchWebsites();
            this.websiteSelection.push(...this.website.websites);
            this.state.activeWebsite = this.website.currentWebsite || this.website.websites[0];
        });

        useEffect(() => {
            (async () => {
                const websiteId = this.state.activeWebsite.id;
                if (!websiteId) {
                    this.env.searchModel.reload();
                } else {
                    const activeWebsitePages = (await this.orm.searchRead(
                        'website.page',
                        [['website_id', '=', websiteId]],
                        ['key']
                    )).map(rec => rec.key);
                    const domain = [
                        '|', ['website_id', '=', websiteId],
                             '&', ['website_id', '=', null],
                                  ['key', 'not in', activeWebsitePages],
                    ];
                    this.env.searchModel.reload({domain});
                }
                this.env.searchModel.search();
            })();
        },() => [this.state.activeWebsite]);
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
        this.state.firstLoad = false;
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
     *        a specific clone on the active website).
     * This is used on first load only to avoid a flickering effect.
     */
    recordFilter(record, records) {
        if (!this.props.firstLoad) {
            return true;
        }
        const websiteId = record.data.website_id && record.data.website_id[0];
        return !this.props.activeWebsite.id
            || this.props.activeWebsite.id === websiteId
            || !websiteId && !records.some(rec => {
                    const recWebsiteId = rec.data.website_id && rec.data.website_id[0];
                    return rec.data.website_url === record.data.website_url
                            && recWebsiteId === this.props.activeWebsite.id;
                });
    }
};
