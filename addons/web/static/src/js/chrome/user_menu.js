odoo.define('web.UserMenu', function (require) {
    "use strict";

    /**
     * This widget is appended by the webclient to the right of the navbar.
     * It displays the avatar and the name of the logged user (and optionally the
     * db name, in debug mode).
     * If clicked, it opens a dropdown allowing the user to perform actions like
     * editing its preferences, accessing the documentation, logging out...
     */

    const config = require('web.config');
    const Dialog = require("web.OwlDialog");
    const framework = require('web.framework');
    const patchMixin = require("web.patchMixin");

    const { useState } = owl.hooks;

    class UserMenu extends owl.Component {
        constructor() {
            super(...arguments);
            this.state = useState({ showShortcuts: false });
        }
        /**
         * @override
         * @returns {Promise}
         */
        mounted() {
            const session = this.env.session;
            super.mounted(...arguments);
            const avatar = this.el.querySelector(".oe_topbar_avatar");
            if (!session.uid) {
                avatar && avatar.setAttribute("src", avatar.getAttribute("data-default-src"));
                return Promise.resolve();
            }
            let topbarName = session.name;
            if (config.isDebug()) {
                topbarName = `${topbarName} (${session.db})`;
            }
            const topbarElement = this.el.querySelector(".oe_topbar_name");
            if (topbarElement) {
                topbarElement.innerText = topbarName;
            }
            const avatarSrc = session.url("/web/image", {
                model: "res.users",
                field: "image_128",
                id: session.uid,
            });
            if (avatar) {
                avatar.setAttribute("src", avatarSrc);
            }
        }

        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------

        doAction(params) {
            return this.trigger("do-action", Object.assign({}, params));
        }

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         * @param {MouseEvent} ev
         */
        _onClickMenu(ev) {
            const menu = ev.target.getAttribute("data-menu");
            this["_onMenu" + menu.charAt(0).toUpperCase() + menu.slice(1)]();
        }
        /**
         * Closes shortcut dialog
         *
         * @private
         */
        _onCloseShortcuts() {
            this.state.showShortcuts = false;
        }
        /**
         * @private
         */
        _onMenuAccount() {
            this.trigger("clear_uncommitted_changes", {
                callback: () => {
                    this.env.services
                        .rpc({ route: "/web/session/account" })
                        .then(function (url) {
                            framework.redirect(url);
                        })
                        .guardedCatch(function (result, ev) {
                            ev.preventDefault();
                            framework.redirect("https://accounts.odoo.com/account");
                        });
                },
            });
        }
        /**
         * @private
         */
        _onMenuDocumentation() {
            window.open("https://www.odoo.com/documentation/user", "_blank");
        }
        /**
         * @private
         */
        _onMenuLogout() {
            this.trigger("clear_uncommitted_changes", {
                callback: this.doAction.bind(this, { action: "logout" }),
            });
        }
        /**
         * @private
         */
        _onMenuSettings() {
            const session = this.env.session;
            this.trigger("clear_uncommitted_changes", {
                callback: () => {
                    this.env.services
                        .rpc({
                            model: "res.users",
                            method: "action_get",
                        })
                        .then((result) => {
                            result.res_id = session.uid;
                            this.doAction({ action: result });
                        });
                },
            });
        }
        /**
         * @private
         */
        _onMenuSupport() {
            window.open("https://www.odoo.com/buy", "_blank");
        }
        /**
         * @private
         */
        _onMenuShortcuts() {
            this.state.showShortcuts = true;
        }
    }

    UserMenu.template = 'UserMenu';
    UserMenu.components = { Dialog }

    return patchMixin(UserMenu);

});
