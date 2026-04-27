import { registry } from "@web/core/registry";
import { generateTour } from "./common";

registry
    .category("web_tour.tours")
    .add("l10n_br_edi_pos.tour_anonymous_order", {
        steps: () => generateTour("000000236"),
    })
    .add("l10n_br_edi_pos.tour_customer_order", {
        // In this case Avalara trimmed our invoiceNumber from 000000255 to 255 for some reason.
        steps: () => generateTour("255", "BR Company Customer"),
    });
