import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { DeliveryButton } from "@pos_urban_piper/point_of_sale_overrirde/app/delivery_button/delivery_button";

patch(Navbar, {
    components: { ...Navbar.components, DeliveryButton },
});
