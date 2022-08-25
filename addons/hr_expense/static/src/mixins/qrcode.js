/** @odoo-module */

import { useService } from "@web/core/utils/hooks";

const { onMounted, onPatched, useRef } = owl;

export const ExpenseMobileQRCode = {
    setup() {
        this._super();
        this.root = useRef('root');
        this.actionService = useService('action');

        onMounted(this.bindAppsIcons);
        onPatched(this.bindAppsIcons);
    },

    bindAppsIcons() {
        const apps = this.root.el.querySelectorAll('.o_expense_mobile_app');
        if (!apps) {
            return;
        }

        const handler = this.handleClick.bind(this);
        for (const app of apps) {
            app.addEventListener('click', handler);
        }
    },

    handleClick(ev) {
        ev.preventDefault();
        ev.stopPropagation();

        const url = ev.currentTarget && ev.currentTarget.href;
        if (!this.env.isSmall) {
            this.actionService.doAction({
                name: this.env._t("Download our App"),
                type: "ir.actions.client",
                tag: 'expense_qr_code_modal',
                target: "new",
                params: { url },
            });
        } else {
            this.actionService.doAction({ type: "ir.actions.act_url", url });
        }
    }
};
