import { Component } from "@odoo/owl";

export class WebsiteSystrayItem extends Component {
    static template = "html_builder.WebsiteSystrayItem";
    static props = {
        onNewPage: { type: Function },
        onEditPage: { type: Function },
    };
}
