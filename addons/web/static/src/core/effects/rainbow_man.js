/** @odoo-module **/

import { browser } from "@web/core/browser/browser";

import { Component, useEffect, useExternalListener, useState } from "@odoo/owl";

/**
 * @typedef Common
 * @property {string} [fadeout='medium'] Delay for rainbowman to disappear.
 *  - 'fast' will make rainbowman dissapear quickly,
 *  - 'medium' and 'slow' will wait little longer before disappearing
 *      (can be used when props.message is longer),
 *  - 'no' will keep rainbowman on screen until user clicks anywhere outside rainbowman
 * @property {string} [imgUrl] URL of the image to be displayed
 *
 * @typedef Simple
 * @property {string} message Message to be displayed on rainbowman card
 *
 * @typedef Custom
 * @property {Component} Component
 * @property {any} [props]
 *
 * @typedef {Common & (Simple | Custom)} RainbowManProps
 */

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
    setup() {
        useExternalListener(document.body, "click", this.closeRainbowMan);
        this.state = useState({ isFading: false });
        this.delay = RainbowMan.rainbowFadeouts[this.props.fadeout];
        if (this.delay) {
            useEffect(
                () => {
                    const timeout = browser.setTimeout(() => {
                        this.state.isFading = true;
                    }, this.delay);
                    return () => browser.clearTimeout(timeout);
                },
                () => []
            );
        }
    }

    onAnimationEnd(ev) {
        if (this.delay && ev.animationName === "reward-fading-reverse") {
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
