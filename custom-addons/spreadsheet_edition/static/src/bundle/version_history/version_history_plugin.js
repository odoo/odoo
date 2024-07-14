/** @odoo-module */
import { UIPlugin } from "@odoo/o-spreadsheet";

export class VersionHistoryPlugin extends UIPlugin {
    constructor(config) {
        super(config);
        this.session = config.session;
    }

    handle(cmd) {
        switch (cmd.type) {
            case "GO_TO_REVISION":
                this.session.revisions.fastForward();
                this.session.revisions.revertTo(cmd.revisionId);
                this.dispatch("START");
                break;
        }
    }
}
