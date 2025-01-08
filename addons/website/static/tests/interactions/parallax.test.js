import { describe, expect, test } from "@odoo/hoot";
import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

import { scroll } from "@odoo/hoot-dom";

setupInteractionWhiteList("website.parallax");
describe.current.tags("interaction_dev");

const getTemplate = function (options = {}) {
    const speed = options.speed || 0;
    return `
        <section style="height: 1000px; background-color: #CCCCFF;"></section>
        <section class="parallax" data-scroll-background-ratio="${speed}" style="min-height: 100px; z-index: -1000;">
            <div class="s_parallax_bg" style="background-color: #CCFFCC; height: 500px; overflow: hidden;"></div>
        </section>
        <section style="height: 1000px; background-color: #FFCCCC;"></section>
    `
}

const simulateScrolls = async function (el, parallaxBg, sectionTop) {
    el.style.overflow = "scroll";
    const spacings = [];
    for (const target of [0, 1000, 1200]) {
        await scroll(el, { y: target });
        document.dispatchEvent(new Event("scroll"));
        await scroll(el, { y: target + 1 });
        document.dispatchEvent(new Event("scroll"));
        const spacing = parallaxBg.getBoundingClientRect().bottom - sectionTop.getBoundingClientRect().bottom;
        spacings.push(spacing);
    }
    return spacings;
}

test("parallax is started when there is an element .parallax", async () => {
    const { core } = await startInteractions(getTemplate());
    expect(core.interactions.length).toBe(1);
});

test("[scroll down] s_parallax_bg move up when the speed is positive", async () => {
    const { el } = await startInteractions(getTemplate({ speed: 2.5 }));
    const spacings = await simulateScrolls(el, el.querySelector(".s_parallax_bg"), el.querySelector("section"))
    for (let i = 0; i < spacings.length - 1; i++) {
        expect(spacings[i] > spacings[i + 1]).toBe(true);
    }
});

test("[scroll down] s_parallax_bg move down when the speed is negative", async () => {
    const { el } = await startInteractions(getTemplate({ speed: -2.5 }));
    const spacings = await simulateScrolls(el, el.querySelector(".s_parallax_bg"), el.querySelector("section"))
    for (let i = 0; i < spacings.length - 1; i++) {
        expect(spacings[i] < spacings[i + 1]).toBe(true);
    }
});

test("[scroll down] s_parallax_bg does not move when the speed is 0", async () => {
    const { el } = await startInteractions(getTemplate({ speed: 0 }));
    const spacings = await simulateScrolls(el, el.querySelector(".s_parallax_bg"), el.querySelector("section"))
    for (let i = 0; i < spacings.length - 1; i++) {
        expect(Math.round(spacings[i] - spacings[i + 1])).toBe(0);
    }
});

test("[scroll down] s_parallax_bg does not move when the speed is 1", async () => {
    const { el } = await startInteractions(getTemplate({ speed: 1 }));
    const spacings = await simulateScrolls(el, el.querySelector(".s_parallax_bg"), el.querySelector("section"))
    for (let i = 0; i < spacings.length - 1; i++) {
        expect(Math.round(spacings[i] - spacings[i + 1])).toBe(0);
    }
});
