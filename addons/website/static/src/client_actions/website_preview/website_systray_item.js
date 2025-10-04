import { Component, useState } from "@odoo/owl";
import { useBus, useService } from "@web/core/utils/hooks";
import { EditInBackendSystrayItem } from "./edit_in_backend";
import { EditWebsiteSystrayItem } from "./edit_website_systray_item";
import { MobilePreviewSystrayItem } from "./mobile_preview_systray";
import { NewContentSystrayItem } from "./new_content_systray_item";
import { PublishSystrayItem } from "./publish_website_systray_item";
import { WebsiteSwitcherSystrayItem } from "./website_switcher_systray_item";
import { registry } from "@web/core/registry";

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
        this.website = useService("website");
        // iframeEl is optional for child components; avoid passing null
        this.state = useState({ iframeEl: undefined, contentUpdateTick: 0 });
        // Resolve iframe asynchronously without blocking initial render
        this.props.iframeLoaded?.then((el) => {
            this.state.iframeEl = el;
        });
        this.website = useService("website");

        // Re-render on content updates to reflect new metadata states
        const websiteSystrayRegistry = registry.category("website_systray");
        useBus(websiteSystrayRegistry, "CONTENT-UPDATED", () => {
            this.state.contentUpdateTick++;
        });
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
            // TODO the functional desire is to have read access on all
            // "website" models for all internal users, but there are many
            // fields preventing that... to review in master (should views just
            // be smarter? should they be more basic in the website app?). This
            // disables the form view access feature for some models that are
            // known to lead to access rights lock. At least, list views are
            // accessible at the moment.
            // See WEBSITE_RECORDS_VIEWS_ACCESS_RIGHTS.
            && (
                !this.website.currentWebsite.metadata.mainObject
                || !['event.event', 'hr.job'].includes(this.website.currentWebsite.metadata.mainObject.model)
                || this.website.currentWebsite.metadata.canPublish
            )
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
        const props = {
            onNewPage: this.props.onNewPage,
            onEditPage: this.props.onEditPage,
        };
        if (this.state.iframeEl) {
            props.iframeEl = this.state.iframeEl;
        }
        return props;
    }
}
