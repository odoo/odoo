import { Component, proxy, useProps } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { useService } from "@web/core/utils/hooks";
import { confirmDraftAction } from "@website/components/dialog/draft_dialog";

export class DraftPreviewSystrayItem extends Component {
    static template = "website.DraftPreviewSystrayItem";
    static components = {
        CheckBox,
    };
    props = useProps({});

    setup() {
        this.websiteService = useService("website");
        this.ui = useService("ui");
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.state = proxy({ isDraftPreview: this.websiteService.isDraftPreview });
    }

    toggleDraftPreview() {
        const newDraftPreview = !this.state.isDraftPreview;
        this.state.isDraftPreview = newDraftPreview;
        this.websiteService.isDraftPreview = newDraftPreview;
        this.reloadIframe();
    }

    async publishDraft() {
        if (await confirmDraftAction(this.dialog, true, false)) {
            await this.orm.call("website", "publish_draft", [this.websiteService.currentWebsiteId]);
            this.exitDraftPreview();
        }
    }

    async deleteDraft() {
        if (await confirmDraftAction(this.dialog, false, false)) {
            await this.orm.call("website", "delete_draft", [this.websiteService.currentWebsiteId]);
            this.exitDraftPreview();
        }
    }

    exitDraftPreview() {
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
        const url = new URL(contentWindow.location.href);
        if (this.state.isDraftPreview) {
            url.searchParams.set("draft_preview", "1");
        } else {
            url.searchParams.delete("draft_preview");
        }
        this.ui.block();
        contentWindow.frameElement.addEventListener("load", () => this.ui.unblock(), {
            once: true,
        });
        contentWindow.location.href = url.pathname + url.search;
    }
}
