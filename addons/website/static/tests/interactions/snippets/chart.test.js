import { setupInteractionWhiteList } from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";
import { patch } from "@web/core/utils/patch";
import { Chart } from "@website/snippets/s_chart/chart";
import { startInteractionsWithSnippet } from "../helpers";

setupInteractionWhiteList("website.chart");

describe.current.tags("interaction_dev");

patch(Chart.prototype, {
    setup() {
        super.setup();
        this.noAnimation = true;
    },
});

test("chart is started when there is an element .s_chart", async () => {
    const { core } = await startInteractionsWithSnippet("s_chart");
    expect(core.interactions).toHaveLength(1);
    await advanceTime(0);
    const canvas = queryOne("canvas");
    const data = canvas.getContext("2d").getImageData(0, 0, canvas.width, canvas.height).data;
    const dataLength = data.length;
    let isCanvasBlank = true;
    for (let i = 0; i < dataLength; i++) {
        if (data[i] != 0) {
            isCanvasBlank = false;
        }
    }
    expect(isCanvasBlank).toBe(false);
});
