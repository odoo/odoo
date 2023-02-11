/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { useEffect } from "@web/core/utils/hooks";

const { Component, hooks } = owl;

/**
 * The RainbowMan widget is the widget displayed by default as a 'fun/rewarding'
 * effect in some cases.  For example, when the user marked a large deal as won,
 * or when he cleared its inbox.
 *
 * This widget is mostly a picture and a message with a rainbow animation around
 * If you want to display a RainbowMan, you probably do not want to do it by
 * importing this file.  The usual way to do that would be to use the effect
 * service (by triggering the 'show_effect' event)
 */
export class RainbowMan extends Component {
    /**
     * @override
     * @constructor
     * @param {Object} [options]
     * @param {string} [options.message] Message to be displayed on rainbowman card
     * @param {string} [options.fadeout='medium'] Delay for rainbowman to disappear. 'fast' will make rainbowman dissapear quickly, 'medium' and 'slow' will wait little longer before disappearing (can be used when options.message is longer), 'no' will keep rainbowman on screen until user clicks anywhere outside rainbowman
     * @param {string} [options.img_url] URL of the image to be displayed
     */
    setup() {
        hooks.useExternalListener(document.body, "click", this.closeRainbowMan);
        const fadeout = "fadeout" in this.props ? this.props.fadeout : "medium";
        const delay = fadeout ? RainbowMan.rainbowFadeouts[fadeout] : false;
        this.delay = typeof delay === "number" ? delay : false;
        if (this.delay !== false) {
            useEffect(
                () => {
                    const timeout = browser.setTimeout(() => {
                        this.el.classList.add("o_reward_fading");
                    }, this.delay);
                    return () => browser.clearTimeout(timeout);
                },
                () => []
            );
        }
    }

    onAnimationEnd(ev) {
        if (this.delay !== false && ev.animationName === "reward-fading-reverse") {
            ev.stopPropagation();
            this.closeRainbowMan();
        }
    }

    closeRainbowMan() {
        this.props.close();
    }
}
RainbowMan.template = "web.RainbowMan";
RainbowMan.rainbowFadeouts = { slow: 4500, medium: 3500, fast: 2000, no: false };
