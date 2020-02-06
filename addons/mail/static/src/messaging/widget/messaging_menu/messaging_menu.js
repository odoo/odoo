odoo.define('mail.messaging.widget.MessagingMenu', function (require) {
'use strict';

const components = {
    MessagingMenu: require('mail.messaging.component.MessagingMenu'),
};

const SystrayMenu = require('web.SystrayMenu');
const Widget = require('web.Widget');

/**
 * Odoo Widget, necessary to instantiate component.
 */
const MessagingMenu = Widget.extend({
    template: 'mail.messaging.widget.MessagingMenu',
    /**
     * @override
     */
    init() {
        this._super(...arguments);
        this.component = undefined;
    },
    /**
     * @override
     */
    async willStart() {
        this._super(...arguments);
        this.env = this.call('messaging', 'getEnv');
    },
    /**
     * @override
     */
    destroy() {
        if (this.component) {
            this.component.destroy();
        }
        this._super(...arguments);
    },
    async on_attach_callback() {
        const MessagingMenuComponent = components.MessagingMenu;
        MessagingMenuComponent.env = this.env;
        this.component = new MessagingMenuComponent(null);
        await this.component.mount(this.el);
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
