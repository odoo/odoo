import { expect, getFixture, test } from "@odoo/hoot";
import { findLowContrastElements } from "@website/builder/plugins/theme/contrast";
import { parseHTML } from "@html_editor/utils/html";

function setupRoot(html) {
    const rootEl = document.createElement("div");
    rootEl.style.backgroundColor = "#ffffff";
    rootEl.style.color = "#000000";
    rootEl.append(parseHTML(document, html));
    getFixture().append(rootEl);
    return rootEl;
}

function getLowContrastTexts(rootEl) {
    return findLowContrastElements(rootEl).map(({ el }) => el.textContent.trim());
}

test("reports dark text on a dark background", () => {
    const rootEl = setupRoot(`
        <section style="background-color: #2E3A3F;">
            <p style="color: #4A4E54; font-size: 16px;">Hidden</p>
            <p style="color: #ffffff;">Readable</p>
        </section>
    `);
    expect(getLowContrastTexts(rootEl)).toEqual(["Hidden"]);
});

test("uses the large text threshold", () => {
    const rootEl = setupRoot(`
        <h2 style="color: #777777; font-size: 24px;">Large enough</h2>
        <h3 style="color: #777777; font-size: 19px; font-weight: 700;">Bold enough</h3>
        <p style="color: #777777; font-size: 19px;">Too small</p>
        <h1 style="color: #999999; font-size: 32px;">Too light</h1>
    `);
    // #777777 on white is 4.48:1, #999999 is 2.85:1.
    expect(getLowContrastTexts(rootEl)).toEqual(["Too small", "Too light"]);
});

test("checks text against its own background, like a button", () => {
    const rootEl = setupRoot(`
        <section style="background-color: #ffffff;">
            <a style="background-color: #714B67; color: #ffffff;">Readable button</a>
            <a style="background-color: #E2DBCF; color: #ffffff;">Unreadable button</a>
        </section>
    `);
    expect(getLowContrastTexts(rootEl)).toEqual(["Unreadable button"]);
});

test("composites a semi-transparent background over its parent", () => {
    const rootEl = setupRoot(`
        <section style="background-color: #000000;">
            <div style="background-color: rgba(255, 255, 255, 0.5);">
                <p style="color: #ffffff;">Washed out</p>
            </div>
        </section>
    `);
    // White on the resulting mid grey is 3.98:1, on plain black it is 21:1.
    expect(getLowContrastTexts(rootEl)).toEqual(["Washed out"]);
});

test("skips text over a background image, parallax, video or filter", () => {
    const rootEl = setupRoot(`
        <section style="background-image: linear-gradient(#000000, #111111);">
            <div><p style="color: #222222;">Over a gradient</p></div>
        </section>
        <section class="s_parallax">
            <span class="s_parallax_bg_wrap"><span class="s_parallax_bg"></span></span>
            <div><p style="color: #ffffff;">Over a parallax photo</p></div>
        </section>
        <section>
            <div class="o_bg_video_container"></div>
            <p style="color: #ffffff;">Over a video</p>
        </section>
        <section>
            <div class="o_we_bg_filter"></div>
            <p style="color: #ffffff;">Over a filter</p>
        </section>
    `);
    expect(findLowContrastElements(rootEl)).toEqual([]);
});

test("skips hidden elements and elements without their own text", () => {
    const rootEl = setupRoot(`
        <section style="background-color: #2E3A3F;">
            <p style="color: #4A4E54; display: none;">Hidden</p>
            <div style="color: #4A4E54;"><span style="color: #ffffff;">Readable</span></div>
        </section>
    `);
    expect(findLowContrastElements(rootEl)).toEqual([]);
});
