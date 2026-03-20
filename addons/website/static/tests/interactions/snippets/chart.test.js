import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";
import { markup } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { Chart } from "@website/snippets/s_chart/chart";

setupInteractionWhiteList("website.chart");

describe.current.tags("interaction_dev");

patch(Chart.prototype, {
    setup() {
        super.setup();
        this.noAnimation = true;
    },
});

test("chart is started when there is an element .s_chart", async () => {
    const { core } = await startInteractions(
        markup`
            <div class="s_chart" data-type="bar" data-legend-position="top" data-tooltip-display="true" data-stacked="false" data-border-width="2"
                data-data="${JSON.stringify({
                    labels: ["First", "Second", "Third", "Fourth", "Fifth"],
                    datasets: [
                        {
                            label: "One",
                            data: ["12", "24", "18", "17", "10"],
                            backgroundColor: "o-color-1",
                            borderColor: "o-color-1",
                        },
                    ],
                })}">
                <h2>A Chart Title</h2>
                <canvas/>
            </div>`.toString()
    );
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
