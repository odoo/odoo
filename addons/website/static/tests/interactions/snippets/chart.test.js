import { expect, test } from "@odoo/hoot";

import { startInteractions, setupInteractionWhiteList } from "../../core/helpers";

import { advanceTime } from "@odoo/hoot-mock";

setupInteractionWhiteList("website.chart");

test("chart interaction does not activate without .s_chart", async () => {
    const { core } = await startInteractions(``);
    expect(core.interactions.length).toBe(0);
});

test("chart interaction activate with .s_chart", async () => {
    const { core, el } = await startInteractions(`
        <div class="s_chart" data-type="bar" data-legend-position="top" data-tooltip-display="true" data-stacked="false" data-border-width="2"
            data-data="{
                &quot;labels&quot;:[&quot;First&quot;,&quot;Second&quot;,&quot;Third&quot;,&quot;Fourth&quot;,&quot;Fifth&quot;],
                &quot;datasets&quot;:[
                    {
                        &quot;label&quot;:&quot;One&quot;,
                        &quot;data&quot;:[&quot;12&quot;,&quot;24&quot;,&quot;18&quot;,&quot;17&quot;,&quot;10&quot;],
                        &quot;backgroundColor&quot;:&quot;o-color-1&quot;,
                        &quot;borderColor&quot;:&quot;o-color-1&quot;
                    }
                ]
            }">
            <h2>A Chart Title</h2>
            <canvas/>
        </div>
    `);
    // TODO investigate why we should use advanceTime
    await advanceTime(0);
    const canvas = el.querySelector('canvas');
    const data = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
    const dataLength = data.length;
    let isBlank = true;
    for (let i = 0; i < dataLength; i++) {
        if (data[i] != 0) {
            isBlank = false;
        }
    }
    expect(core.interactions.length).toBe(1);
    expect(isBlank).toBe(false);
});
