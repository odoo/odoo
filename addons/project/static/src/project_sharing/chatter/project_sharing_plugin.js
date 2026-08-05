import { Plugin, signal, t } from "@odoo/owl";

export class ProjectSharingPlugin extends Plugin {
    isFollower = signal(false, { type: t.boolean() });
    projectSharingId = signal(undefined, { type: t.number().optional() });
}
