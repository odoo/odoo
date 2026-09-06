import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { RainbowMan } from "./rainbow_man";
import { Plugin, usePlugin, useScope } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { services } from "@web/core/services";
import { OverlayPlugin } from "@web/core/overlay/overlay_plugin";

const effectRegistry = registry.category("effects");

// -----------------------------------------------------------------------------
// RainbowMan effect
// -----------------------------------------------------------------------------

/**
 * Handles effect of type "rainbow_man". If the effects aren't disabled, returns
 * the RainbowMan component to instantiate and its props. If the effects are
 * disabled, displays the message in a notification.
 *
 * @param {Object} [params={}]
 * @param {Translation} [params.message="Well Done!"]
 *    The message in the notice the rainbowman holds or the content of the notification if effects are disabled
 *    Can be a simple a string
 *    Can be a string representation of html (prefer component if you want interactions in the DOM)
 * @param {string} [params.img_url="/web/static/img/smile.svg"]
 *    The url of the image to display inside the rainbow
 * @param {"slow"|"medium"|"fast"|"no"} [params.fadeout="medium"]
 *    Delay for rainbowman to disappear
 *    'fast' will make rainbowman dissapear quickly
 *    'medium' and 'slow' will wait little longer before disappearing (can be used when options.message is longer)
 *    'no' will keep rainbowman on screen until user clicks anywhere outside rainbowman
 * @param {typeof import("@odoo/owl").Component} [params.Component]
 *    Custom Component class to instantiate inside the Rainbow Man
 * @param {Object} [params.props]
 *    If params.Component is given, its props can be passed with this argument
 */
function rainbowMan(params = {}) {
    const notification = useService("notification");
    let message = params.message;
    if (message instanceof Element) {
        console.log(
            "Providing an HTML element to an effect is deprecated. Note that all event handlers will be lost."
        );
        message = message.outerHTML;
    } else if (!message) {
        message = _t("Well Done!");
    }
    if (user.showEffect) {
        /** @type {import("./rainbow_man").RainbowManProps} */
        const props = {
            imgUrl: params.img_url || "/web/static/img/smile.svg",
            fadeout: params.fadeout || "medium",
            message,
            Component: params.Component,
            props: params.props,
        };
        return { Component: RainbowMan, props };
    }
    notification.add(message);
}
effectRegistry.add("rainbow_man", rainbowMan);

// -----------------------------------------------------------------------------
// Effect service
// -----------------------------------------------------------------------------

export class EffectPlugin extends Plugin {
    /** @private */
    overlay = usePlugin(OverlayPlugin);
    /** @private */
    scope = useScope();

    /**
     * @param {Object} [params] various params depending on the type of effect
     * @param {string} [params.type="rainbow_man"] the effect to display
     */
    add(params = {}) {
        const type = params.type || "rainbow_man";
        const effect = effectRegistry.get(type);
        const { Component, props } = this.scope.run(() => effect(params)) || {};
        if (Component) {
            const remove = this.overlay.add(Component, {
                ...props,
                close: () => remove(),
            });
        }
    }
}

services.add(EffectPlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of the effect service are removed
 * -----------------------------------------------------------------------------
 */
export const effectService = {
    dependencies: ["overlay"],
    start() {
        return usePlugin(EffectPlugin);
    },
};

registry.category("services").add("effect", effectService);
