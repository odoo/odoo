import { NewContentSystrayItem } from "./new_content_systray_item";
import { EditWebsiteSystrayItem } from "./edit_website_systray_item";
import { Component, onWillStart } from "@odoo/owl";
import { PublishSystrayItem } from "./publish_website_systray_item";
import { useService } from "@web/core/utils/hooks";
import { MobilePreviewSystrayItem } from "./mobile_preview_systray";

export class WebsiteSystrayItem extends Component {
    static template = "html_builder.WebsiteSystrayItem";
    static props = {
        onNewPage: { type: Function },
        onEditPage: { type: Function },
        iframeLoaded: { type: Object },
    };
    static components = {
        MobilePreviewSystrayItem,
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

    get canPublish() {
        return this.website.currentWebsite && this.website.currentWebsite.metadata.canPublish;
    }

    get isRestrictedEditor() {
        return this.website.isRestrictedEditor;
    }

    get editWebsiteSystrayItemProps() {
        return {
            onNewPage: this.props.onNewPage,
            onEditPage: this.props.onEditPage,
            iframeEl: this.iframeEl,
        };
    }
}
