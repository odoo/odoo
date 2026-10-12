import { patch } from "@web/core/utils/patch";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";

patch(ActionPanel.prototype, {
    get initialWidth() {
        return super.initialWidth || this.store.discuss.INSPECTOR_WIDTH;
    },
    get minWidth() {
        return super.minWidth || this.store.discuss.INSPECTOR_WIDTH;
    },
});
