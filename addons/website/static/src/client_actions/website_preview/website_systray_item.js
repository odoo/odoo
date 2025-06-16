import { Component, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { EditInBackendSystrayItem } from "./edit_in_backend";
import { EditWebsiteSystrayItem } from "./edit_website_systray_item";
import { MobilePreviewSystrayItem } from "./mobile_preview_systray";
import { NewContentSystrayItem } from "./new_content_systray_item";
import { PublishSystrayItem } from "./publish_website_systray_item";
import { WebsiteSwitcherSystrayItem } from "./website_switcher_systray_item";

export class WebsiteSystrayItem extends Component {
    static template = "website.WebsiteSystrayItem";
    static props = {
        onNewPage: { type: Function },
        onEditPage: { type: Function },
        iframeLoaded: { type: Object },
    };
    static components = {
        MobilePreviewSystrayItem,
        WebsiteSwitcherSystrayItem,
        EditInBackendSystrayItem,
        NewContentSystrayItem,
        EditWebsiteSystrayItem,
        PublishSystrayItem,
    };

    setup() {
        onWillStart(async () => {
            this.iframeEl = await this.props.iframeLoaded;
        });
        this.website = useService("website");
    }

    get hasMultiWebsites() {
        return this.website.websites.length > 1;
    }

    get canPublish() {
        return this.website.currentWebsite && this.website.currentWebsite.metadata.canPublish;
    }

    get isRestrictedEditor() {
        return this.website.isRestrictedEditor;
    }

    get hasEditableRecordInBackend() {
        return (
            this.website.currentWebsite && this.website.currentWebsite.metadata.editableInBackend
        );
    }

    get canEdit() {
        return (
            this.website.currentWebsite &&
            (this.website.currentWebsite.metadata.editable ||
                this.website.currentWebsite.metadata.translatable)
        );
    }

    get editWebsiteSystrayItemProps() {
        return {
            onNewPage: this.props.onNewPage,
            onEditPage: this.props.onEditPage,
            iframeEl: this.iframeEl,
        };
    }
}
