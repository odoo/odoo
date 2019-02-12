odoo.define('mail.widget.MessagingMenu', function (require) {
"use strict";

const MessagingMenuComponent = require('mail.component.MessagingMenu');
const EnvMixin = require('mail.widget.EnvMixin');

const SystrayMenu = require('web.SystrayMenu');
const Widget = require('web.Widget');

/**
 * Odoo Widget, necessary to instanciate a root OWL widget.
 */
const MessagingMenu = Widget.extend(EnvMixin, {
    DEBUG: true,
    template: 'mail.widget.MessagingMenu',
    init() {
        this._super.apply(this, arguments);
        this.component = undefined;

        if (this.DEBUG) {
            window.systray_messaging_menu = this;
        }
    },
    /**
     * @override {web.Widget}
     */
    willStart() {
        return Promise.all([
            this._super.apply(this, arguments),
            this.getEnv()
        ]);
    },
    /**
     * @override {web.Widget}
     */
    destroy() {
        if (this.component) {
            this.component.destroy();
        }
        this._super.apply(this, arguments);
    },
    async on_attach_callback() {
        this.component = new MessagingMenuComponent(this.env);
        await this.component.mount(this.$el[0]);
        // unwrap
        this.el.parentNode.insertBefore(this.component.el, this.el);
        this.el.parentNode.removeChild(this.el);
    },
});

// Systray menu items display order matches order in the list
// lower index comes first, and display is from right to left.
// For messagin menu, it should come before activity menu, if any
// otherwise, it is the next systray item.
const activityMenuIndex = SystrayMenu.Items.findIndex(SystrayMenuItem =>
    SystrayMenuItem.prototype.name === 'activity_menu');
if (activityMenuIndex > 0) {
    SystrayMenu.Items.splice(activityMenuIndex, 0, MessagingMenu);
} else {
    SystrayMenu.Items.push(MessagingMenu);
}

return MessagingMenu;

});
