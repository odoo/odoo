import { Plugin, signal } from "@odoo/owl";

export class RenameThreadPlugin extends Plugin {
    editingName = signal(false);
}
