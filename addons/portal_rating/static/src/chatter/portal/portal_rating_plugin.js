import { Plugin, signal } from "@odoo/owl";

export class PortalRatingPlugin extends Plugin {
    reviewChatter = signal(false);
}
