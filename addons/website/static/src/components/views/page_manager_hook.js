import { useEnv } from "@web/owl2/utils";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { AddPageDialog } from "@website/components/dialog/add_page_dialog";
import { onWillStart, proxy, usePlugin } from "@odoo/owl";
import { DebugModePlugin } from "@web/core/debug_mode_plugin";

/**
 * Asks the user to confirm the update of the URL of some pages, as the links
 * pointing to the old URLs are not redirected.
 *
 * @param {Object} dialog - the dialog service
 * @returns {Promise<boolean>} true if the update is confirmed
 */
export function confirmPageUrlUpdate(dialog) {
    return new Promise((resolve) => {
        dialog.add(
            ConfirmationDialog,
            {
                body: _t("Some links pointing to these old URLs may return a 404 error"),
                confirmLabel: _t("Update"),
                confirm: () => resolve(true),
                cancelLabel: _t("Cancel"),
                cancel: () => resolve(false),
            },
            { onClose: () => resolve(false) }
        );
    });
}

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
    const debugMode = usePlugin(DebugModePlugin);
    const websiteSelection = debugMode.isActive() ? [{ id: 0, name: _t("All Websites") }] : [];
    const state = proxy({
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

    return {
        get websites() {
            const activeId = state.activeWebsite.id;
            return websiteSelection.map((website) => {
                const isActive = website.id === activeId;
                return { ...website, isActive };
            });
        },
        createWebsiteContent,
    };
}
