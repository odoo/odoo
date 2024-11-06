import { expect, test } from "@odoo/hoot";

import { startInteractions, setupInteractionWhiteList } from "../../core/helpers";
import { advanceTime } from "@odoo/hoot-mock";

setupInteractionWhiteList("website.countdown");

test("countdown interaction does not activate without .s_countdown", async () => {
    const { core } = await startInteractions(``);
    expect(core.interactions.length).toBe(0);
});

test("countdown interaction activate with a .s_countdown", async () => {
    const endTime = 12345678900;
    const { core } = await startInteractions(`
        <div style="background-color: white;"> 
            <section class="s_countdown pt48 pb48"
             data-display="dhms" 
             data-end-action="nothing" 
             data-size="175"
             data-layout="circle" 
             data-layout-background="none"
             data-progress-bar-style="surrounded" 
             data-progress-bar-weight="thin"
             id="countdown-section"
             data-text-color="o-color-1"
             data-layout-background-color="400"
             data-progress-bar-color="o-color-1"
             data-end-time=${endTime}>
                <div class="container">
                    <div class="s_countdown_canvas_wrapper" 
                    style="
                        display: flex;
                        justify-content: center;
                        align-items: center;">
                    </div>
                </div>
            </section>
        </div>
    `);
    expect(core.interactions.length).toBe(1);
});

test("countdown interaction update the canvas for seconds correctly", async () => {
    const endTime = 12345678900;
    const { core, el } = await startInteractions(`
        <div style="background-color: white;"> 
            <section class="s_countdown pt48 pb48"
             data-display="dhms" 
             data-end-action="nothing" 
             data-size="175"
             data-layout="circle" 
             data-layout-background="none"
             data-progress-bar-style="surrounded" 
             data-progress-bar-weight="thin"
             id="countdown-section"
             data-text-color="o-color-1"
             data-layout-background-color="400"
             data-progress-bar-color="o-color-1"
             data-end-time=${endTime}>
                <div class="container">
                    <div class="s_countdown_canvas_wrapper" 
                    style="
                        display: flex;
                        justify-content: center;
                        align-items: center;">
                    </div>
                </div>
            </section>
        </div>
    `);

    // time T

    const canvas1Els = el.querySelectorAll('canvas');
    const canvas1Hours = canvas1Els[1];
    const data1Hours = canvas1Hours.getContext('2d').getImageData(0, 0, canvas1Hours.width, canvas1Hours.height).data;
    const canvas1Seconds = canvas1Els[3];
    const data1Seconds = canvas1Seconds.getContext('2d').getImageData(0, 0, canvas1Seconds.width, canvas1Seconds.height).data;

    await advanceTime(1000);

    // time T + 1s

    const canvas2Els = el.querySelectorAll('canvas');
    const canvas2Hours = canvas2Els[1];
    const data2Hours = canvas2Hours.getContext('2d').getImageData(0, 0, canvas2Hours.width, canvas2Hours.height).data;
    const canvas2Seconds = canvas2Els[3];
    const data2Seconds = canvas2Seconds.getContext('2d').getImageData(0, 0, canvas2Seconds.width, canvas2Seconds.height).data;

    await advanceTime(1000);

    // time T + 2s

    const canvas3Els = el.querySelectorAll('canvas');
    const canvas3Hours = canvas3Els[1];
    const data3Hours = canvas3Hours.getContext('2d').getImageData(0, 0, canvas3Hours.width, canvas3Hours.height).data;
    const canvas3Seconds = canvas3Els[3];
    const data3Seconds = canvas3Seconds.getContext('2d').getImageData(0, 0, canvas3Seconds.width, canvas3Seconds.height).data;

    // Compare canvases

    const data1HoursLength = data1Hours.length;
    const data2HoursLength = data2Hours.length;
    const data3HoursLength = data3Hours.length;

    const data1SecondsLength = data1Seconds.length;
    const data2SecondsLength = data2Seconds.length;
    const data3SecondsLength = data3Seconds.length;

    expect(data1HoursLength).toBe(data2HoursLength)
    expect(data1SecondsLength).toBe(data2SecondsLength)
    expect(data2HoursLength).toBe(data3HoursLength)
    expect(data2SecondsLength).toBe(data3SecondsLength)

    let wasHourCanvasChanged12 = false;
    for (let i = 0; i < data1HoursLength; i++) {
        if (Math.abs(data1Hours[i] - data2Hours[i]) > 1) {
            wasHourCanvasChanged12 = true;
            break;
        }
    }

    let wasHourCanvasChanged23 = false;
    for (let i = 0; i < data2HoursLength; i++) {
        if (Math.abs(data2Hours[i] - data3Hours[i]) > 1) {
            wasHourCanvasChanged23 = true;
            break;
        }
    }

    let wasSecondCanvasChanged12 = false;
    for (let i = 0; i < data1SecondsLength; i++) {
        if (data1Seconds[i] != data2Seconds[i]) {
            wasSecondCanvasChanged12 = true;
            break;
        }
    }

    let wasSecondCanvasChanged23 = false;
    for (let i = 0; i < data2SecondsLength; i++) {
        if (data2Seconds[i] != data3Seconds[i]) {
            wasSecondCanvasChanged23 = true;
            break;
        }
    }

    expect(wasHourCanvasChanged12 && wasHourCanvasChanged23).toBe(false);
    expect(wasSecondCanvasChanged12 && wasSecondCanvasChanged23).toBe(true);
});
