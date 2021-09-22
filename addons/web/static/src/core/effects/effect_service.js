/** @odoo-module **/

import { registry } from "../registry";
import { EffectContainer } from "./effect_container";
import { RainbowMan } from "./rainbow_man";

const { EventBus } = owl.core;

const effectRegistry = registry.category("effects");

// -----------------------------------------------------------------------------
// RainbowMan effect
// -----------------------------------------------------------------------------

/**
 * Handles effect of type "rainbow_man". If the effects aren't disabled, returns
 * the RainbowMan component to instantiate and its props. If the effects are
 * disabled, displays the message in a notification.
 *
 * @param {Object} env
 * @param {Object} [params={}]
 * @param {string} [params.message="Well Done"]
 *    The message in the notice the rainbowman holds or the content of the notification if effects are disabled
 *    Can be a simple a string
 *    Can be a string representation of html (prefer component if you want interactions in the DOM)
 * @param {boolean} [params.img_url="/web/static/img/smile.svg"]
 *    The url of the image to display inside the rainbow
 * @param {boolean} [params.messageIsHtml]
 *    Set to true if the message encodes html, s.t. it will be correctly inserted into the DOM.
 * @param {"slow"|"medium"|"fast"|"no"} [params.fadeout="medium"]
 *    Delay for rainbowman to disappear
 *    'fast' will make rainbowman dissapear quickly
 *    'medium' and 'slow' will wait little longer before disappearing (can be used when options.message is longer)
 *    'no' will keep rainbowman on screen until user clicks anywhere outside rainbowman
 * @param {owl.Component} [params.Component=RainbowMan]
 *    Component class to instantiate (if effects aren't disabled)
 * @param {Object} [params.props]
 *    If params.Component is given, its props can be passed with this argument
 */
function rainbowMan(env, params = {}) {
    let message = params.message;
    if (message instanceof jQuery) {
        console.log(
            "Providing a jQuery element to an effect is deprecated. Note that all event handlers will be lost."
        );
        message = message.html();
    } else if (message instanceof Element) {
        console.log(
            "Providing an HTML element to an effect is deprecated. Note that all event handlers will be lost."
        );
        message = message.outerHTML;
    } else if (!message) {
        message = env._t("well Done!");
    }
    if (env.services.user.showEffect) {
        return {
            Component: params.Component || RainbowMan,
            props: {
                imgUrl: params.img_url || "/web/static/img/smile.svg",
                fadeout: params.fadeout,
                message,
                messageIsHtml: params.messageIsHtml || false,
                ...params.props,
            },
        };
    }
    env.services.notification.add(message);
}
effectRegistry.add("rainbow_man", rainbowMan);

// -----------------------------------------------------------------------------
// Effect service
// -----------------------------------------------------------------------------

export const effectService = {
    start(env) {
        const bus = new EventBus();
        registry.category("main_components").add("EffectContainer", {
            Component: EffectContainer,
            props: { bus },
        });
        let effectId = 0;

        /**
         * @param {Object} params various params depending on the type of effect
         * @param {string} [params.type="rainbow_man"] the effect to display
         */
        function add(params) {
            const type = params.type || "rainbow_man";
            const effect = effectRegistry.get(type);
            const { Component, props } = effect(env, params) || {};
            if (Component) {
                bus.trigger("UPDATE", { Component, props, id: effectId++ });
            }
        }

        return { add };
    },
};

registry.category("services").add("effect", effectService);
