import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import { registry } from "@web/core/registry";
import * as RestaurantAppointment from "@pos_restaurant_appointment/../tests/tours/utils/restaurant_appointment_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as ProductScreenPos from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
import { delay } from "@odoo/hoot-dom";

const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };

registry.category("web_tour.tours").add("RestaurantAppointmentTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Make sure there is a currently active order.
            FloorScreen.clickTable("4"),
            ProductScreen.clickDisplayedProduct("Coca-Cola", true),

            // Check that the booking gantt view is shown.
            {
                content:
                    "Wait few ms before clicking on Booking to ensure gantt view will be shown",
                isActive: ["auto"],
                trigger: "body",
                async run() {
                    await delay(1000);
                },
            },
            {
                trigger: ".pos-leftheader button:contains('Booking')",
                run: "click",
            },
            {
                content: "Check that the booking gantt view is shown",
                trigger: ".pos-content .o_action_manager .o_gantt_view",
            },
            {
                content: "Close the booking gantt view",
                trigger: ".o_control_panel:contains('Manage Bookings')",
            },
            Chrome.clickPlanButton(),
            RestaurantAppointment.appointmentLabel(5, "Test Lunch"),

            // Going back to the table, it should still be possible to add items
            FloorScreen.clickTable("4"),
            ProductScreen.clickDisplayedProduct("Coca-Cola", true),
        ].flat(),
});
