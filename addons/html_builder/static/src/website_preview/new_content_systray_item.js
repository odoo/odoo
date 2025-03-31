import { NewContentModal } from "@html_builder/website_preview/new_content_modal";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class NewContentSystrayItem extends Component {
    static template = "html_builder.NewContentSystrayItem";
    static components = { NewContentModal };
    static props = {
        onNewPage: Function,
    };

    setup() {
        this.website = useService("website");
        this.websiteContext = useState(this.website.context);
    }

    onClick() {
        this.websiteContext.showNewContentModal = !this.websiteContext.showNewContentModal;
    }
}
