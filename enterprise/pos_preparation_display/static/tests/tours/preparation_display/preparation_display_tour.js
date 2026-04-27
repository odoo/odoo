import * as PreparationDisplay from "@pos_preparation_display/../tests/tours/preparation_display/utils/preparation_display_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PreparationDisplayTourProductName", {
    steps: () =>
        [PreparationDisplay.containsProduct("Configurable Chair (Red, Metal, Leather)")].flat(),
});
