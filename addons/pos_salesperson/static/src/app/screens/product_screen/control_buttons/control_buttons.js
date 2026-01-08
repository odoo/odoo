import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { SalespersonButton } from "@pos_salesperson/app/screens/product_screen/control_buttons/salesperson_button/salesperson_buutton";
import { patch } from "@web/core/utils/patch";

patch(ControlButtons, {
    components: {
        ...ControlButtons.components,
        SalespersonButton,
    },
});
