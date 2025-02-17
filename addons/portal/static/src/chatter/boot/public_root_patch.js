import { PublicRoot } from "@web/legacy/js/public/public_root";
import { patch } from "@web/core/utils/patch";

patch(PublicRoot.prototype, {
    /**
     * @override
     * wait for chatter lazy loaded bundle before lunching the MainComponentsContainer
     */
    async createMainComponent(env) {
        await odoo.portalChatterReady;
        return super.createMainComponent(...arguments);
    },
});
