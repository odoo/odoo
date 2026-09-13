// @ts-check
/** @odoo-module native */

import { registry } from "@web/core/registry";
import { BottomSheet } from "@web/ui/bottom_sheet/bottom_sheet";
import { makeOverlayPresenter } from "@web/ui/overlay/presenter";

/**
 * @typedef {import("@web/ui/popover/popover_service").PopoverServiceAddOptions & {
 * onBack?: () => void;
 * preventDismissOnContentScroll?: boolean;
 * }} BottomSheetServiceAddOptions
 * @typedef {BottomSheetService["add"]} BottomSheetServiceAddFunction
 */

/** @type {Set<BottomSheetService>} */
const activeServices = new Set();

class BottomSheetService {
    /** @param {{ overlay: any }} services */
    constructor({ overlay }) {
        this.openCount = 0;
        this.present = makeOverlayPresenter({
            overlay,
            component: BottomSheet,
            scope: "bottom_sheet",
            toProps: (options) => ({
                onBack: options.onBack,
                preventDismissOnContentScroll: options.preventDismissOnContentScroll,
            }),
            onOpen: () => {
                this.openCount++;
                this.syncBodyClasses();
            },
            onClosed: () => {
                this.openCount = Math.max(0, this.openCount - 1);
                this.syncBodyClasses();
            },
        });
    }

    syncBodyClasses() {
        if (this.openCount) {
            activeServices.add(this);
        } else {
            activeServices.delete(this);
        }
        let openCount = 0;
        for (const service of activeServices) {
            openCount += service.openCount;
        }
        document.body.classList.toggle("bottom-sheet-open", openCount > 0);
        document.body.classList.toggle("bottom-sheet-open-multiple", openCount > 1);
    }

    /**
     * @param {HTMLElement} target
     * @param {import("@odoo/owl").ComponentConstructor} component
     * @param {object} [props]
     * @param {BottomSheetServiceAddOptions} [options]
     * @returns {(removeParams?: any) => Promise<void>}
     */
    add(target, component, props = {}, options = {}) {
        return this.present(target, component, props, options);
    }

    destroy() {
        this.openCount = 0;
        this.syncBodyClasses();
    }
}

const bottomSheetService = {
    dependencies: ["overlay"],
    /**
     * @param {import("@web/env").OdooEnv} _
     * @param {{ overlay: any }} services
     * @returns {BottomSheetService}
     */
    start(_, services) {
        return new BottomSheetService(services);
    },
};

registry.category("services").add("bottom_sheet", bottomSheetService);
