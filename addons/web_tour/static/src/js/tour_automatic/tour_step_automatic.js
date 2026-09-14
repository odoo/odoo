/** @odoo-module native */
import "@web_tour/js/tour_automatic/tour_helpers_hoot";

import hoot from "@odoo/hoot-dom";
import { getTag } from "@web/core/utils/dom/xml";
import { MacroMutationObserver } from "@web/core/utils/macro";
import { TourHelpers } from "@web_tour/js/tour_automatic/tour_helpers";
import { tourState } from "@web_tour/js/tour_state";
import { TourStep } from "@web_tour/js/tour_step";
import { serializeChanges, serializeMutation } from "@web_tour/js/utils/tour_utils";

async function waitForMutations(target = document, timeout = 1000 / 16) {
    return new Promise((resolve) => {
        let observer;
        let timer;
        const mutationList = [];
        function onMutation(mutations) {
            mutationList.push(...(mutations || []));
            clearTimeout(timer);
            timer = setTimeout(() => {
                observer.disconnect();
                resolve(mutationList);
            }, timeout);
        }
        observer = new MacroMutationObserver(onMutation);
        observer.observe(target);
        onMutation([]);
    });
}
export class TourStepAutomatic extends TourStep {
    skipped = false;
    error = "";
    constructor(data, tour, index) {
        super(data, tour);
        this.index = index;
        this.tourConfig = tourState.getCurrentConfig();
    }

    async checkForUndeterminisms(initialElement, delay) {
        if (delay <= 0 || !initialElement) {
            return;
        }
        const tagName = initialElement.tagName?.toLowerCase();
        if (["body", "html"].includes(tagName) || !tagName) {
            return;
        }
        const snapshot = initialElement.cloneNode(true);
        const mutations = await waitForMutations(initialElement, delay);
        let reason;
        if (!hoot.isVisible(initialElement)) {
            reason = `Initial element is no longer visible`;
        } else if (!initialElement.isEqualNode(snapshot)) {
            reason =
                `Initial element has changed:\n` +
                JSON.stringify(serializeChanges(snapshot, initialElement), null, 2);
        } else if (mutations.length) {
            const changes = [...new Set(mutations.map(serializeMutation))];
            reason =
                `Initial element has mutated ${mutations.length} times:\n` +
                JSON.stringify(changes, null, 2);
        }
        if (reason) {
            throw new Error(
                `Potential non deterministic behavior found in ${delay}ms for trigger ${this.trigger}.\n${reason}`,
            );
        }
    }

    get describeWhyIFailed() {
        const errors = [];
        if (this.element) {
            errors.push(`Element has been found.`);
            if (this.isUIBlocked) {
                errors.push("BUT: DOM is blocked by UI.");
            }
            if (!this.elementIsInModal) {
                errors.push(
                    `BUT: It is not allowed to do action on an element that's below a modal.`,
                );
            }
            if (!this.elementIsEnabled) {
                errors.push(
                    `BUT: Element is not enabled. TIP: You can use :enable to wait the element is enabled before doing action on it.`,
                );
            }
            if (!this.documentIsReady) {
                errors.push(`BUT: the document is not ready ([is-ready='false']).`);
            }
        } else {
            const checkElement = hoot.queryFirst(this.trigger);
            if (checkElement) {
                errors.push(`Element has been found.`);
                errors.push(
                    `BUT: Element is not visible. TIP: You can use :not(:visible) to force the search for an invisible element.`,
                );
            } else {
                errors.push(`Element (${this.trigger}) has not been found.`);
            }
        }
        return errors;
    }

    async doAction() {
        if (this.skipped) {
            return false;
        }
        const actionHelper = new TourHelpers(this.element);
        if (typeof this.run === "function") {
            return await this.run.call({ anchor: this.element }, actionHelper);
        } else if (typeof this.run === "string") {
            let lastResult = null;
            for (const todo of this.run.split("&&")) {
                const m = String(todo)
                    .trim()
                    .match(/^(?<action>\w*) *\(? *(?<arguments>.*?)\)?$/);
                const action = m.groups?.action;
                const method = actionHelper[action];
                if (typeof method !== "function") {
                    throw new Error(
                        `Tour step action "${action}" is unknown. Actions come from ` +
                            "TourHelpers or from the 'web_tour.helpers' registry; an " +
                            "addon adding one must register it there, because this " +
                            "runtime lives in the lazily-loaded 'web_tour.automatic' " +
                            "bundle and patching its class from another bundle reaches " +
                            "a different copy.",
                    );
                }
                lastResult = await method.call(actionHelper, m.groups?.arguments);
            }
            return lastResult;
        }
    }

    /** @returns {(HTMLElement|Boolean)} */
    findTrigger() {
        if (!this.active) {
            this.skipped = true;
            return true;
        }
        const visible = !/:(hidden|visible)\b/.test(this.trigger);
        this.element = hoot.queryFirst(this.trigger, { visible });
        if (this.element) {
            return (!this.hasAction || (!this.isUIBlocked && this.documentIsReady)) &&
                this.elementIsEnabled &&
                this.elementIsInModal
                ? this.element
                : false;
        }
        return false;
    }

    get isUIBlocked() {
        return (
            document.body.classList.contains("o_ui_blocked") ||
            document.querySelector(".o_blockUI") ||
            document.querySelector(".o_is_blocked")
        );
    }

    // a public page's body says `is-ready="false"` until its interactions
    // have started; a step that acts before that is undone by them (a form
    // prefilled over what the step typed), while a step that only observes
    // may look at a page that is still booting. A page without the
    // attribute -- the backend -- is ready when its element is
    get documentIsReady() {
        if (this.trigger.match(/\[is-ready=(true|false)\]/)) {
            return true;
        }
        const parentFrame = hoot.getParentFrame(this.element);
        const body = parentFrame ? parentFrame.contentDocument.body : document.body;
        return body?.hasAttribute("is-ready")
            ? body.getAttribute("is-ready") === "true"
            : true;
    }

    get elementIsInModal() {
        if (this.hasAction) {
            const overlays = hoot.queryFirst(
                ".popover, .o-we-command, .o-we-toolbar, .o_notification",
            );
            const modal = hoot.queryFirst(".modal:visible:not(.o_inactive_modal):last");
            if (modal && !overlays && !this.trigger.startsWith("body")) {
                return (
                    modal.contains(hoot.getParentFrame(this.element)) ||
                    modal.contains(this.element)
                );
            }
        }
        return true;
    }

    get elementIsEnabled() {
        const isTag = (array) => array.includes(getTag(this.element, true));
        if (this.hasAction) {
            if (isTag(["input", "textarea"])) {
                return hoot.isEditable(this.element);
            } else if (isTag(["button", "select"])) {
                return !this.element.disabled;
            }
        }
        return true;
    }

    get hasAction() {
        return ["string", "function"].includes(typeof this.run) && !this.skipped;
    }
}
