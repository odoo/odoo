import { DiscussAvatar } from "@mail/core/common/discuss_avatar";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { BurgerMenu } from "@web/webclient/burger_menu/burger_menu";

Object.assign(BurgerMenu.components, { DiscussAvatar });

patch(BurgerMenu.prototype, {
    setup() {
        super.setup();
        this.store = useService("mail.store");
    },
});
