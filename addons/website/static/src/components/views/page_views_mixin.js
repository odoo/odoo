/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import {useService} from "@web/core/utils/hooks";
import { AddPageDialog } from "@website/components/dialog/add_page_dialog";
import { onWillStart, useState } from "@odoo/owl";

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
        this.orm = useService('orm');

        this.websiteSelection = odoo.debug ? [{id: 0, name: _t("All Websites")}] : [];

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
            return this.dialog.add(AddPageDialog, {
                websiteId: this.state.activeWebsite.id,
            });
        }
        const action = this.props.context.create_action;
        if (action) {
            if (/^\//.test(action)) {
                const url = await rpc(action);
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
