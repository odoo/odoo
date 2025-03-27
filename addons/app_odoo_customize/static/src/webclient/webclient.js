/** @odoo-module **/

import { WebClient } from "@web/webclient/webclient";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

patch(WebClient.prototype, "app_odoo_customize.WebClient", {
    setup() {
        // 处理 navbar 全局可配置位置
        var self = this;
        self._super.apply(this, arguments);
        this.state.navbar_pos_pc = session.app_navbar_pos_pc || 'top';
        this.state.navbar_pos_mobile = session.app_navbar_pos_mobile || 'top';
        if (self.env.isSmall)
            this.state.navbar_pos = this.state.navbar_pos_mobile;
        else
            this.state.navbar_pos = this.state.navbar_pos_pc;
        if (this.state.navbar_pos === 'bottom') {
            document.body.className += ' navbar_pos_bottom';
        }

        const app_system_name = session.app_system_name || 'odooAi';
        // zopenerp is easy to grep
        this.title.setParts({ zopenerp: app_system_name });

    }
});
