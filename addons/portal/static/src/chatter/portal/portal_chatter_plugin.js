import { Plugin, signal } from "@odoo/owl";

export class PortalChatterPlugin extends Plugin {
    displayRating = signal(false);
    inFrontendPortalChatter = signal(false);
}
