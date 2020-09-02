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
        /**
         * @override
         * @constructor
         * @param {Object} [props]
         * @param {string} [props.message] Message to be displayed on rainbowman card
         * @param {string} [props.fadeout='medium'] Delay for rainbowman to disappear. 'fast' will make rainbowman dissapear quickly, 'medium' and 'slow' will wait little longer before disappearing (can be used when options.message is longer), 'no' will keep rainbowman on screen until user clicks anywhere outside rainbowman
         * @param {string} [props.img_url] URL of the image to be displayed
         */
        constructor(parent, props) {
            super(...arguments);
            const rainbowDelay = {
                very_slow: 8500,
                slow: 4500,
                medium: 3500,
                fast: 2000,
                no: false,
            };
            this.options = _.defaults(props || {}, {
                fadeout: "medium",
                img_url: "/web/static/src/img/smile.svg",
                message: this.env._t("Well Done!"),
            });
            this.delay = rainbowDelay[this.options.fadeout];
        }
        async willStart() {
            await super.willStart(...arguments);
            const templates = await owl.utils.loadFile("/web/static/src/xml/rainbow_man.xml");
            this.env.qweb.addTemplates(templates);
        }
        /**
         * @override
         */
        mounted() {
            const self = this;
            super.mounted(...arguments);
            // destroy rainbow man when the user clicks outside
            // this is done in a setTimeout to prevent the click that triggered the
            // rainbow man to close it directly
            setTimeout(function () {
                self.env.bus.on("click", self, function (ev) {
                    if (ev.originalEvent && ev.target.className.indexOf("o_reward") === -1) {
                        this.destroy();
                    }
                });
            });
            if (this.delay) {
                setTimeout(function () {
                    self.el && self.el.classList.add("o_reward_fading");
                    setTimeout(function () {
                        self.destroy();
                    }, 600); // destroy only after fadeout animation is completed
                }, this.delay);
            }
            if (this.options.message) {
                if (typeof this.options.message === 'string') {
                    this.el.querySelector(".o_reward_msg_content").innerText = this.options.message;
                } else {
                    this.el.querySelector(".o_reward_msg_content").appendChild(this.options.message[0]);
                }
            }
        }
    }

    RainbowMan.template = 'rainbow_man.notification';

    return RainbowMan;

});
