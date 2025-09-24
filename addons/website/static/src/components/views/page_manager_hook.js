import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { AddPageDialog } from "@website/components/dialog/add_page_dialog";
import { onWillStart, useEnv, useState } from "@odoo/owl";

/**
 * Used to share code and keep the same behaviour on different types of 'website
 * content' views:
 * - Trigger the 'new content' dialogs when 'CREATE' button is clicked.
 * - Add a website selector on ControlPanel (that will be used by the renderer
 * to filter content).
 */
export function usePageManager({ resModel, createAction }) {
    const env = useEnv();
    const website = useService("website");
    const dialog = useService("dialog");
    const actionService = useService("action");
    const websiteSelection = odoo.debug ? [{ id: 0, name: _t("All Websites") }] : [];
    const state = useState({
        activeWebsite: undefined,
    });

    onWillStart(async () => {
        // `fetchWebsites()` already done by parent PageSearchModel
        websiteSelection.push(...website.websites);
        state.activeWebsite = await env.searchModel.getCurrentWebsite();
    });

    async function createWebsiteContent() {
        if (resModel === "website.page") {
            return dialog.add(AddPageDialog, {
                websiteId: state.activeWebsite.id,
            });
        }
        if (createAction) {
            if (/^\//.test(createAction)) {
                const url = await rpc(createAction);
                website.goToWebsite({ path: url, edition: true });
                return;
            }
            actionService.doAction(createAction, {
                onClose: (infos) => {
                    if (infos) {
                        website.goToWebsite({ path: infos.path });
                    }
                },
                props: {
                    onSave: (record, params) => {
                        if (record.resId && params.computePath) {
                            const path = params.computePath();
                            actionService.doAction({
                                type: "ir.actions.act_window_close",
                                infos: { path },
                            });
                        }
                    },
                },
            });
        }
    }

    function selectWebsite(website) {
        state.activeWebsite = website;
        env.searchModel.notifyWebsiteChange(website.id);
    }
    return {
        get websites() {
            const activeId = state.activeWebsite.id;
            return websiteSelection.map((website) => {
                const isActive = website.id === activeId;
                return { ...website, isActive };
            });
        },
        createWebsiteContent,
        selectWebsite,
    };
}
