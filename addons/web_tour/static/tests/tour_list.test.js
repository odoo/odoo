import { describe, expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import {
    defineModels,
    defineWebModels,
    mountView,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { TourRecorderPlugin } from "@web_tour/tour_recorder/tour_recorder_plugin";
import { Tour, TourStep } from "./tour_models";

describe.current.tags("desktop");

defineWebModels();
defineModels([Tour, TourStep]);

test("clicking the Record button starts the tour recorder", async () => {
    let startTourRecorderCalls = 0;
    patchWithCleanup(TourRecorderPlugin.prototype, {
        async startTourRecorder() {
            startTourRecorderCalls++;
            return super.startTourRecorder(...arguments);
        },
    });

    await mountView({
        resModel: "web_tour.tour",
        type: "list",
        arch: `<list js_class="tour_list"><field name="name"/></list>`,
    });

    expect(".o_button_tour_recorder").toHaveCount(1);
    await click(".o_button_tour_recorder");
    await animationFrame();

    expect(startTourRecorderCalls).toBe(1);
});
