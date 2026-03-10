import { useState } from "@web/owl2/utils";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { getSkipDialogKey, DraftActionDialog } from "@website/components/dialog/draft_dialog";

export class DraftPreviewSystrayItem extends Component {
    static template = "website.DraftPreviewSystrayItem";
    static components = {
        CheckBox,
    };
    static props = {};

    setup() {
        this.websiteService = useService("website");
        this.ui = useService("ui");
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.state = useState({ isDraftPreview: this.websiteService.isDraftPreview });
    }

    toggleDraftPreview() {
        const newDraftPreview = !this.state.isDraftPreview;
        this.state.isDraftPreview = newDraftPreview;
        this.websiteService.isDraftPreview = newDraftPreview;
        this.reloadIframe();
    }

    async publishDraft() {
        let removeDialog = () => {};
        const localStorageKey = getSkipDialogKey(true, false);
        if (!browser.localStorage.getItem(localStorageKey)) {
            const shouldPublish = await new Promise((resolve) => {
                removeDialog = this.dialog.add(DraftActionDialog, {
                    pageOnly: false,
                    publish: true,
                    confirm: () => resolve(true),
                    discard: () => resolve(false),
                });
            });
            removeDialog();
            if (!shouldPublish) {
                return;
            }
        }
        await this.orm.call("website", "publish_draft", [this.websiteService.currentWebsiteId]);
        this.state.isDraftPreview = false;
        this.websiteService.isDraftPreview = false;
        this.reloadIframe();
    }

    async deleteDraft() {
        let removeDialog = () => {};
        const localStorageKey = getSkipDialogKey(false, false);
        if (!browser.localStorage.getItem(localStorageKey)) {
            const shouldPublish = await new Promise((resolve) => {
                removeDialog = this.dialog.add(DraftActionDialog, {
                    pageOnly: false,
                    isPublishing: false,
                    confirm: () => resolve(true),
                    discard: () => resolve(false),
                });
            });
            removeDialog();
            if (!shouldPublish) {
                return;
            }
        }
        await this.orm.call("website", "delete_draft", [this.websiteService.currentWebsiteId]);
        this.state.isDraftPreview = false;
        this.websiteService.isDraftPreview = false;
        this.reloadIframe();
    }

    reloadIframe() {
        // Reload the iframe with or without the draft_preview query param
        const contentWindow = this.websiteService.contentWindow;
        if (!contentWindow) {
            return;
        }
        const { origin, pathname, search } = contentWindow.location;
        const url = new URL(pathname + search, origin);
        if (this.state.isDraftPreview) {
            url.searchParams.set("draft_preview", "1");
        } else {
            url.searchParams.delete("draft_preview");
        }
        this.ui.block();
        const onIframeLoaded = () => {
            this.ui.unblock();
            contentWindow.frameElement.removeEventListener("load", onIframeLoaded);
        };

        contentWindow.frameElement.addEventListener("load", onIframeLoaded);
        contentWindow.location.href = url.pathname + url.search;
    }
}
