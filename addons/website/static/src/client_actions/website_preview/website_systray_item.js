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
            this.website.currentWebsite &&
            this.website.currentWebsite.metadata.editableInBackend &&
            // TODO the functional desire is to have read access on all
            // "website" models for all internal users, but there are many
            // fields preventing that... to review in master (should views just
            // be smarter? should they be more basic in the website app?). This
            // disables the form view access feature for some models that are
            // known to lead to access rights lock. At least, list views are
            // accessible at the moment.
            // See WEBSITE_RECORDS_VIEWS_ACCESS_RIGHTS.
            (!this.website.currentWebsite.metadata.mainObject ||
                !["event.event", "hr.job"].includes(
                    this.website.currentWebsite.metadata.mainObject.model
                ) ||
                this.website.currentWebsite.metadata.canPublish)
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
