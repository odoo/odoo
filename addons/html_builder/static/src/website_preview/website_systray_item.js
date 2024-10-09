import { EditWebsiteSystrayItem } from "./edit_website_systray_item";
import { Component, onWillStart } from "@odoo/owl";

export class WebsiteSystrayItem extends Component {
    static template = "html_builder.WebsiteSystrayItem";
    static props = {
        onNewPage: { type: Function },
        onEditPage: { type: Function },
        iframeLoaded: { type: Object },
    };
    static components = {
        EditWebsiteSystrayItem,
    };

    setup() {
        onWillStart(async () => {
            this.iframeEl = await this.props.iframeLoaded;
        });
    }

    get editWebsiteSystrayItemProps() {
        return {
            onNewPage: this.props.onNewPage,
            onEditPage: this.props.onEditPage,
            iframeEl: this.iframeEl,
        };
    }
}
