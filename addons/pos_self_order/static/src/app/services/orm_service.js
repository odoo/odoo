import { ORM, ormService } from "@web/core/orm_service";
import { patch } from "@web/core/utils/patch";

patch(ORM.prototype, {
    call(model, action, args = [], kwargs = {}) {
        if (model !== "pos.payment.method") {
            return super.call(...arguments);
        }
        const params = {
            access_token: this.env.services.self_order.access_token,
            args,
            kwargs,
        };
        return this.rpc(`/kiosk/payment_method_action/${action}`, params, {
            silent: this._silent,
        });
    },
});

patch(ormService, {
    start(env) {
        const orm = super.start(...arguments);
        orm.env = env;
        return orm;
    },
});
