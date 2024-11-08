import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { BalanceButton } from "@pos_six/app/components/balance_button/balance_button";
import { patch } from "@web/core/utils/patch";

patch(Navbar, {
    components: { ...Navbar.components, BalanceButton },
});
