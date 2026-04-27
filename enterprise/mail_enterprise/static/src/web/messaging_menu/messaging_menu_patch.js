import { MessagingMenu } from "@mail/core/public_web/messaging_menu";

import { patch } from "@web/core/utils/patch";

import { useBackButton } from "@web_mobile/js/core/hooks";

patch(MessagingMenu.prototype, {
    setup() {
        super.setup();
        useBackButton(
            () => this.dropdown.close(),
            () => this.dropdown.isOpen
        );
    },
});
