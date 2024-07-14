/** @odoo-module **/
import { HomeMenu } from "@web_enterprise/webclient/home_menu/home_menu";
import { url } from "@web/core/utils/urls";
import { patch } from "@web/core/utils/patch";
import { onMounted, onWillUnmount } from "@odoo/owl";

patch(HomeMenu.prototype, {
    setup() {
        super.setup();
        if (!this.menus.getMenu("root").backgroundImage) {
            return;
        }
        this.backgroundImageUrl = url("/web/image", {
            id: this.env.services.company.currentCompany.id,
            model: "res.company",
            field: "background_image",
        });

        onMounted(() => {
            document.body.classList.add("o_home_menu_background");
            document.body.classList.toggle(
                "o_home_menu_background_custom",
                this.menus.getMenu("root").backgroundImage
            );
        });

        onWillUnmount(() => {
            document.body.classList.remove(
                "o_home_menu_background",
                "o_home_menu_background_custom"
            );
        });
    },
});
