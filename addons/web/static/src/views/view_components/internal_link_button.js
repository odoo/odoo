import { Component } from "@odoo/owl";

export class InternalLinkButton extends Component {
    static components = {};
    static template = "web.InternalLinkButton";
    static props = {
        onClick: { type: Function },
    };
}
