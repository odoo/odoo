/** @odoo-module **/

import { registry } from "../../core/registry";

const { EventBus } = owl.core;

export function convertRainBowMessage(message) {
    if (message instanceof jQuery) {
        console.log(
            "Providing jQuery to an effect is deprecated. Note that all event handlers will be lost."
        );
        return message.html();
    } else if (message instanceof Element) {
        console.log(
            "Providing HTML to an effect is deprecated. Note that all event handlers will be lost."
        );
        return message.outerHTML;
    } else if (typeof message === "string") {
        return message;
    }
}

export const effectService = {
    dependencies: ["notification", "user"],
    start(env, { notification, user }) {
        const bus = new EventBus();
        let effectId = 0;

        /**
         * This private method checks if the effects are disabled.
         * If so, it makes a notification from the message attribute of an effect and
         * doesn't trigger the effect at all.
         * @param {Object} effect The effect to display
         */
        function applyEffect(effect) {
            if (!user.showEffect) {
                notification.add(effect.message, { sticky: false });
            } else {
                bus.trigger("UPDATE", effect);
            }
        }

        /**
         * Display a rainbowman effect
         *
         * @param {Object} [params={}]
         * @param {string|Function} [params.message="Well Done"]
         *    The message in the notice the rainbowman holds or the content of the notification if effects are disabled
         *    Can be a simple a string
         *    Can be a string representation of html (prefer component if you want interactions in the DOM)
         *    Can be a function returning a string (like _t)
         * @param {"slow"|"medium"|"fast"|"no"} [params.fadeout="medium"]
         *    Delay for rainbowman to disappear
         *    'fast' will make rainbowman dissapear quickly
         *    'medium' and 'slow' will wait little longer before disappearing (can be used when options.message is longer)
         *    'no' will keep rainbowman on screen until user clicks anywhere outside rainbowman
         * @param {owl.Component} [params.Component]
         *    Component class to instantiate
         *    It this option is set, the message option is ignored unless effect are disbled
         *    Then, the message param is used to display a notification
         * @param {Object} [params.props]
         *    If a component is used, its props can be passed with this argument
         */
        function rainbowMan(params = {}) {
            const effect = Object.assign({
                imgUrl: "/web/static/img/smile.svg",
                fadeout: params.fadeout,
                id: ++effectId,
                message: convertRainBowMessage(params.message) || env._t("Well Done!"),
                Component: params.Component,
                props: params.props,
            });
            applyEffect(effect);
        }

        /**
         * Display an effect
         * This is a dispatcher for the effect. Usefull if the request for effect comes
         * from the server.
         * In the weblient, use the more specific effect functions.
         *
         * @param {string} type
         *    What effect to create
         *      - rainbowman
         * @param {Object} [params={}]
         *    All the options for the effect.
         *    The options get passed to the more specific effect methods.
         */
        function create(type, params = {}) {
            switch (type.replace("_", "").toLowerCase()) {
                case "rainbowman":
                    return rainbowMan(params);
                default:
                    throw new Error("NON_IMPLEMENTED_EFFECT");
            }
        }

        return { create, rainbowMan, bus };
    },
};

registry.category("services").add("effect", effectService);
