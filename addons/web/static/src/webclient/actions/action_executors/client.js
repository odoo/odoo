// @ts-check
/** @odoo-module native */

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { pick } from "@web/core/utils/collections/objects";

import { nextActionDepth } from "../action_constants.js";

const actionRegistry = registry.category("actions");

/** @import { ActionManager, ActionOptions, ClientAction } from "../action_service.js" */

/**
 * @param {ClientAction} action
 * @param {ActionOptions} options
 * @param {ActionManager} am
 */
export async function executeClientAction(action, options, am) {
    const clientAction = actionRegistry.get(/** @type {string} */ (action.tag));
    action.path ||= clientAction.path;
    if (clientAction.prototype instanceof Component) {
        if (action.target !== "new" && !options.newWindow) {
            if (!(await am.confirmLeave(pick(options, "forceLeave")))) {
                return;
            }
            if (clientAction.target) {
                action.target = clientAction.target;
            }
        }
        const props = /** @type {any} */ (clientAction).extractProps?.(action) || {};
        const controller = am.makeController({
            Component: /** @type {any} */ (clientAction),
            action,
            ...am.getActionInfo(action, { ...props, ...options.props }),
        });
        controller.displayName ||= clientAction.displayName?.toString() || "";
        return am.updateUI(controller, options);
    } else {
        const token = am.navigation.snapshot();
        const next = await /** @type {any} */ (clientAction)(am.env, action, options);
        if (next) {
            token.throwIfSuperseded();
            const depth = nextActionDepth(options);
            return am.doAction(next, { ...options, _actionDepth: depth });
        }
        options.onClose?.();
    }
}
