import { EventBus, Plugin } from "@odoo/owl";
import { useBus } from "@web/core/utils/hooks";

/**
 * Communication between the components of a BoM or MO overview, e.g. to fold
 * or unfold all the lines from the control panel, to tell the overview which
 * lines are folded/unfolded, and to reload it.
 */
export class MrpOverviewPlugin extends Plugin {
    bus = new EventBus();

    /**
     * @param {boolean} isFolded
     */
    toggleFoldAll(isFolded) {
        this.bus.trigger("toggle-fold-all", { isFolded });
    }

    /**
     * @param {(isFolded: boolean) => any} handler
     */
    onToggleFoldAll(handler) {
        useBus(this.bus, "toggle-fold-all", (ev) => handler(ev.detail.isFolded));
    }

    /**
     * @param {string[]} indexes
     * @param {boolean} isFolded
     */
    updateFolded(indexes, isFolded) {
        this.bus.trigger("update-folded", { indexes, isFolded });
    }

    /**
     * @param {(foldInfo: { indexes: string[], isFolded: boolean }) => any} handler
     */
    onUpdateFolded(handler) {
        useBus(this.bus, "update-folded", (ev) => handler(ev.detail));
    }

    reload() {
        this.bus.trigger("reload");
    }

    /**
     * @param {() => any} handler
     */
    onReload(handler) {
        useBus(this.bus, "reload", handler);
    }
}
