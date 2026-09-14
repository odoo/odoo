// @ts-check
/** @odoo-module native */

import { EventBus, reactive } from "@odoo/owl";
import { makeLogger } from "@web/core/debug/debug_logger";
import { AppEvent } from "@web/core/events";
import { registry } from "@web/core/registry";
import { publishEnclosingScopeResolver } from "@web/core/utils/active_element_scope";
import { makeActiveElementStack } from "@web/ui/active_element_stack";
import { BlockUI } from "@web/ui/block/block_ui";
import { describeNode } from "@web/ui/describe_node";
import { mainComponentEntry } from "@web/ui/main_components_container";
import { getMediaQueryLists, utils } from "@web/ui/viewport";

export {
    getFirstAndLastTabableElements,
    useActiveElement,
} from "@web/ui/active_element";

const log = makeLogger("web.ui");

class UiService {
    /** @param {import("@web/env").OdooEnv} env */
    constructor(env) {
        this.env = env;
        this.bus = new EventBus();
        /** @type {() => void} */
        this._onMediaChange = () => {};
        /** @type {MediaQueryList[]} */
        this.subscribedMedias = [];
        this.blockCount = 0;
        this.activeElements = makeActiveElementStack();
        /** @type {(() => void) | null} */
        this.withdrawScopeResolver = null;

        this.size = this.getSize();
        /** @type {Document | HTMLElement} */
        this.activeElement = document;
        this.isBlocked = false;
        // through utils, not SIZES directly: point_of_sale patches utils.isSmall
        // to widen "small" to tablets, and env.isSmall must follow
        this.isSmall = utils.isSmall(this);
    }

    setup() {
        registry
            .category("main_components")
            .add("BlockUI", mainComponentEntry(BlockUI));

        this._onMediaChange = () => this.updateSize();
        this.subscribedMedias = getMediaQueryLists();
        for (const media of this.subscribedMedias) {
            media.addEventListener?.("change", this._onMediaChange);
        }

        Object.defineProperty(this.env, "isSmall", {
            configurable: true,
            get: () => this.isSmall,
        });
        this.withdrawScopeResolver = publishEnclosingScopeResolver(
            (node) => this.getScopeOf(node),
            () => this.activeElement,
        );
    }

    /** @returns {number} */
    getSize() {
        return utils.getSize();
    }

    updateSize() {
        const size = this.getSize();
        if (size === this.size) {
            return;
        }
        this.size = size;
        this.isSmall = utils.isSmall(this);
        log.logic("resize", () => ({ size, isSmall: this.isSmall }));
        this.bus.trigger(AppEvent.RESIZE);
    }

    /** @param {{ message?: string, delay?: number }} [data] */
    block(data) {
        this.blockCount++;
        this.isBlocked = true;
        log.logic("block", () => ({
            blockCount: this.blockCount,
            message: data?.message,
        }));
        if (this.blockCount === 1) {
            this.bus.trigger(AppEvent.BLOCK, {
                message: data?.message,
                delay: data?.delay,
            });
        }
    }

    unblock() {
        this.blockCount--;
        log.logic("unblock", () => ({ blockCount: this.blockCount }));
        if (this.blockCount < 0) {
            console.warn(
                "Unblock ui was called more times than block, you should only unblock the UI if you have previously blocked it.",
            );
            this.blockCount = 0;
            return;
        }
        if (this.blockCount === 0) {
            this.isBlocked = false;
            this.bus.trigger(AppEvent.UNBLOCK);
        }
    }

    publishActiveElement() {
        this.activeElement = this.activeElements.current;
        log.logic("activeElement", () => ({
            current: describeNode(this.activeElement),
            depth: this.activeElements.depth,
        }));
        this.bus.trigger(AppEvent.ACTIVE_ELEMENT_CHANGED, this.activeElement);
    }

    /** @param {HTMLElement} el */
    activateElement(el) {
        this.activeElements.activate(el);
        this.publishActiveElement();
    }

    /** @param {HTMLElement} el */
    deactivateElement(el) {
        if (this.activeElements.deactivate(el)) {
            this.publishActiveElement();
        } else {
            log.logic("deactivateElement", () => ({
                el: describeNode(el),
                known: false,
                depth: this.activeElements.depth,
            }));
        }
    }

    /** @param {Node} el */
    getActiveElementOf(el) {
        return this.activeElements.activeElementOf(el);
    }

    /**
     * @param {Node | null} node
     * @returns {Document | HTMLElement}
     */
    getScopeOf(node) {
        return this.activeElements.scopeOf(node);
    }

    destroy() {
        this.withdrawScopeResolver?.();
        this.withdrawScopeResolver = null;
        for (const media of this.subscribedMedias) {
            media.removeEventListener?.("change", this._onMediaChange);
        }
        this.subscribedMedias = [];
        this.activeElements.reset();
        this.activeElement = this.activeElements.current;
        this.blockCount = 0;
        this.isBlocked = false;
        // deleting, not restoring makeEnv's throwing getter: a component that
        // renders once more while the env is being torn down reads undefined
        // instead of taking the teardown down with it
        delete (/** @type {any} */ (this.env).isSmall);
    }
}

export const uiService = {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @returns {UiService}
     */
    start(env) {
        const service = reactive(new UiService(env));
        service.setup();
        return service;
    },
};

registry.category("services").add("ui", uiService);
