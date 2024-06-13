/* global posmodel */
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import { run } from "@point_of_sale/../tests/tours/utils/common";
import { registry } from "@web/core/registry";
import { TourError } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add("LargeDBTour", {
    test: true,
    steps: () =>
        [
            Dialog.confirm("Open session"),
            run(() => {
                const time = performance.getEntriesByName("first-contentful-paint")[0].startTime;
                throw new TourError(
                    `time was ${time}, for a db with ${
                        posmodel.models["product.product"].getAll().length
                    } products`
                );
            }),
        ].flat(),
});
