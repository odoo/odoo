/** @odoo-module **/

import { MessagingMenu } from '@mail/components/messaging_menu/messaging_menu';

import SystrayMenu from 'web.SystrayMenu';
import Widget from 'web.Widget';

/**
 * Odoo Widget, necessary to instantiate component.
 */
const MessagingMenuWidget = Widget.extend({
    template: 'mail.widgets.MessagingMenu',
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
    destroy() {
        if (this.component) {
            this.component.destroy();
        }
        this._super(...arguments);
    },
    async on_attach_callback() {
        this.component = new MessagingMenu(null);
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
    SystrayMenu.Items.splice(activityMenuIndex, 0, MessagingMenuWidget);
} else {
    SystrayMenu.Items.push(MessagingMenuWidget);
}

export default MessagingMenuWidget;
