odoo.define('web.RainbowMan', function (require) {
"use strict";

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

class RainbowMan extends owl.Component {
    static async display(props, options) {
        let target = document.body;
        let parent = null;
        if (options) {
            target = options.target || target;
            parent = options.parent || parent;
        }
        const rainbowman = new this(parent, props);
        await rainbowman.mount(target);
        return rainbowman;
    }
    /**
     * @override
     * @constructor
     * @param {Object} [options]
     * @param {string} [options.message] Message to be displayed on rainbowman card
     * @param {string} [options.fadeout='medium'] Delay for rainbowman to disappear. 'fast' will make rainbowman dissapear quickly, 'medium' and 'slow' will wait little longer before disappearing (can be used when options.message is longer), 'no' will keep rainbowman on screen until user clicks anywhere outside rainbowman
     * @param {string} [options.img_url] URL of the image to be displayed
     */
    constructor() {
        super(...arguments);
        owl.hooks.useExternalListener(document.body, 'click', this._closeRainbowMan);
        const fadeout = 'fadeout' in this.props ? this.props.fadeout : 'medium';
        const delay = this.constructor.rainbowDelay[fadeout];
        this.delay = typeof delay === 'number' ? delay : false;
        this.img_url = this.props.img_url || '/web/static/src/img/smile.svg';
    }
    mounted() {
        if (this.delay !== false) {
            setTimeout(
                () => {
                    if (!this.__owl__.isDestroyed) {
                        this.el.classList.add('o_reward_fading')
                    }
                },
                this.delay
            );
        }
        super.mounted();
    }
    /**
     * Message could be: Jquery / HTMLElement or String
     * should be String representing HTML tree
     */
    get message() {
        const message = this.props.message;
        if (message instanceof jQuery) {
            return message.html();
        }
        if (message instanceof Element) {
            return message.outerHTML;
        }
        if (typeof message === 'string') {
            return message;
        }
        return this.env._t('Well Done!');
    }
    _onAnimationEnd(ev) {
        if (this.delay !== false && ev.animationName === 'reward-fading-reverse') {
            this._closeRainbowMan();
        }
    }
    _closeRainbowMan() {
        this.trigger('close-rainbowman');
        this.destroy();
    }
}
RainbowMan.rainbowDelay = {slow: 4500, medium: 3500, fast: 2000, no: false};
RainbowMan.template = 'rainbow_man.notification';
RainbowMan.xmlDependencies = ['/web/static/src/xml/rainbow_man.xml'];

return RainbowMan;
});
