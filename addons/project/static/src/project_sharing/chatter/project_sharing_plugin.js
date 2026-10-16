import { Plugin, signal, t } from "@odoo/owl";

export class ProjectSharingPlugin extends Plugin {
    showCcField = signal(false);
    projectSharingId = signal(undefined, { type: t.number().optional() });
}
