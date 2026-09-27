import { Plugin, signal, t } from "@odoo/owl";

export class ProjectSharingPlugin extends Plugin {
    projectSharingId = signal(undefined, { type: t.number().optional() });
}
