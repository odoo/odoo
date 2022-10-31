/** @odoo-module **/

import { HomeMenu } from "@web_enterprise/webclient/home_menu/home_menu";
import { patch } from "@web/core/utils/patch";


patch(HomeMenu.prototype, 'mail.home_menu_focus', {
    /**
     * @override
     */
    _onKeydownFocusInput(ev) {
        const isOnchatWindow = document.activeElement && document.activeElement.classList.contains('o_ChatWindow');
        const isCopyCmd = ev.key === 'c' && (ev.ctrlKey || ev.metaKey);
        // prevent focusing the home menu hence loosing the selected
        // text when copying a message on a chat window.
        if (isOnchatWindow && (['Control', 'Meta'].includes(ev.key) || isCopyCmd)) {
            return;
        }
        this._super(ev);
    },
});
