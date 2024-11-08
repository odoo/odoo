import { Component } from "@odoo/owl";

export class WebsiteSystrayItem extends Component {
    static template = "mysterious_egg.WebsiteSystrayItem";
    static props = {
        onNewPage: { type: Function },
        onEditPage: { type: Function },
    };
}
