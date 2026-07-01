import { Plugin, signal } from "@odoo/owl";

export class ProjectSharingPlugin extends Plugin {
    projectSharingId = signal(undefined);
}
