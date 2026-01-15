import { ImStatus } from "@mail/core/common/im_status";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { UserMenu } from "@web/webclient/user_menu/user_menu";

Object.assign(UserMenu.components, { ImStatus });

patch(UserMenu.prototype, {
    setup() {
        super.setup();
        this.store = useService("mail.store");
    },
});
