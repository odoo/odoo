import { ImStatus } from "@mail/core/common/im_status";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { BurgerMenu } from "@web/webclient/burger_menu/burger_menu";

Object.assign(BurgerMenu.components, { ImStatus });

patch(BurgerMenu.prototype, {
    setup() {
        super.setup();
        this.store = useService("mail.store");
    },
});
