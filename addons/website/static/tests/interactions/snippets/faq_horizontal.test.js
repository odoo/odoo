import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";

import {
    setupTest,
    customScroll,
} from "../header/helpers";

import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

setupInteractionWhiteList([
    "website.header_standard",
    "website.header_fixed",
    "website.header_disappears",
    "website.header_fade_out",
    "website.faq_horizontal",
]);
describe.current.tags("interaction_dev");

const getTemplate = function (headerType, useHiddenOnScroll) {
    return `
    <header class="${headerType}" style="background-color:#CCFFCC">
        ${useHiddenOnScroll ? `<div class="o_header_hide_on_scroll" style="height: 20px; background-color:#CCFF33;"></div>` : ""}
        <div style="height: ${useHiddenOnScroll ? "30px" : "50px"}; background-color:#33FFCC;"></div>
    </header>
    <main>
        <section class="s_faq_horizontal o_colored_level" data-snippet="s_faq_horizontal" data-name="Topics List">
            <div class="container">
                <div data-name="Topic" class="s_faq_horizontal_entry col-12 mb-2 pt16 pb32 o_colored_level">
                    <article class="row">
                    <hgroup class="col-lg-4" role="heading" aria-level="3">
                        <div class="s_faq_horizontal_entry_title position-lg-sticky pb-lg-3 transition-base overflow-auto" style="top: 79.9773px; max-height: calc(-119.977px + 100vh);">
                            <h3 class="h5-fs">Getting Started</h3>
                            <p class="o_small text-muted">Getting started with our product is a breeze, thanks to our well-structured and comprehensive onboarding process.</p>
                        </div>
                    </hgroup>
                    <span class="col-lg-7 offset-lg-1 d-block">
                        <p>We understand that the initial setup can be daunting, especially if you are new to our platform, so we have designed a step-by-step guide to walk you through every stage, ensuring that you can hit the ground running.<br></p>
                        <img src="/web/image/website.s_faq_horizontal_default_image_1" class="img img-fluid rounded" style="width: 100% !important;" alt="" loading="lazy" data-mimetype="image/jpeg" data-original-id="278" data-original-src="/website/static/src/img/snippets_demo/s_faq_horizontal_1.jpg" data-mimetype-before-conversion="image/jpeg">
                        <p><br>The first step in the onboarding process is <b>account creation</b>. This involves signing up on our platform using your email address or social media accounts. Once you’ve created an account, you will receive a confirmation email with a link to activate your account. Upon activation, you’ll be prompted to complete your profile, which includes setting up your preferences, adding any necessary payment information, and selecting the initial features or modules you wish to use.</p>
                        <p>Next, you will be introduced to our <b>setup wizard</b>, which is designed to guide you through the basic configuration of the platform. The wizard will help you configure essential settings such as language, time zone, and notifications.</p>
                        <p><a href="#">Read More <i class="fa fa-angle-right" role="img"></i></a></p>
                    </span>
                    </article>
                </div>
                <div data-name="Topic" class="s_faq_horizontal_entry col-12 mb-2 pt16 pb32 o_colored_level">
                    <article class="row">
                    <hgroup class="col-lg-4" role="heading" aria-level="3">
                        <div class="s_faq_horizontal_entry_title position-lg-sticky pb-lg-3 transition-base overflow-auto" style="top: 79.9773px; max-height: calc(-119.977px + 100vh);">
                            <h3 class="h5-fs">Updates and Improvements</h3>
                            <p class="o_small text-muted">We are committed to continuous improvement, regularly releasing updates and new features based on user feedback and technological advancements.</p>
                        </div>
                    </hgroup>
                    <span class="col-lg-7 offset-lg-1 d-block">
                        <p>Our development team works tirelessly to enhance the platform's performance, security, and functionality, ensuring it remains at the cutting edge of innovation.</p>
                        <p>Each update is thoroughly tested to guarantee compatibility and reliability, and we provide detailed release notes to keep you informed of new features and improvements. </p>
                        <div data-snippet="s_chart" data-name="Chart" class="s_chart" data-type="line" data-legend-position="top" data-tooltip-display="true" data-stacked="false" data-border-width="1" data-data="{&quot;labels&quot;:[&quot;v15&quot;,&quot;v16&quot;,&quot;v17&quot;,&quot;v18&quot;],&quot;datasets&quot;:[{&quot;label&quot;:&quot;Improvements&quot;,&quot;data&quot;:[&quot;12&quot;,&quot;24&quot;,&quot;48&quot;,&quot;200&quot;],&quot;backgroundColor&quot;:&quot;o-color-1&quot;,&quot;borderColor&quot;:&quot;o-color-1&quot;}]}" data-max-value="250" data-ticks-min="NaN" data-ticks-max="250">
                            <canvas height="291" style="box-sizing: border-box; display: block; height: 265px; width: 530px;" width="583"></canvas>
                        </div>
                        <p><br>Users can participate in beta testing programs, providing feedback on upcoming releases and influencing the future direction of the platform. By staying current with updates, you can take advantage of the latest tools and features, ensuring your business remains competitive and efficient.</p>
                    </span>
                    </article>
                </div>
                <div data-name="Topic" class="s_faq_horizontal_entry col-12 mb-2 pt16 pb32 o_colored_level">
                    <article class="row">
                    <hgroup class="col-lg-4" role="heading" aria-level="3">
                        <div class="s_faq_horizontal_entry_title position-lg-sticky pb-lg-3 transition-base overflow-auto" style="top: 79.9773px; max-height: calc(-119.977px + 100vh);">
                            <h3 class="h5-fs">Support and Resources</h3>
                            <p class="o_small text-muted">We are committed to providing exceptional support and resources to help you succeed with our platform.</p>
                        </div>
                    </hgroup>
                    <span class="col-lg-7 offset-lg-1 d-block">
                        <p>Our support team is available 24/7 to assist with any issues or questions you may have, ensuring that help is always within reach.</p>
                        <p>Additionally, we offer a comprehensive knowledge base, including detailed documentation, video tutorials, and community forums where you can connect with other users and share insights.</p>
                        <p>We also provide regular updates and new features based on user feedback, ensuring that our platform continues to evolve to meet your needs.</p>
                        <p><a href="#" class="btn btn-secondary">Documentation</a></p>
                    </span>
                    </article>
                </div>
            </div>
        </section>
    </main>
    `
}

const HEADER_SIZE = 50
const DEFAULT_OFFSET = 16

test("faq_horizontal is started when there is an element .s_faq_horizontal", async () => {
    const { core } = await startInteractions(getTemplate("", false));
    expect(core.interactions.length).toBe(1);
});

test.tags("desktop")("faq_horizontal updates titles position with a o_header_standard", async () => {
    const { el, core } = await startInteractions(getTemplate("o_header_standard", false));
    expect(core.interactions.length).toBe(2);
    const wrapwrap = el.querySelector("#wrapwrap");
    const title = el.querySelector(".s_faq_horizontal_entry_title");
    await setupTest(core, wrapwrap);
    // Since the header does not move in Hoot, we have to take into
    // account the scroll in the test when checking where the bottom
    // of the header is (ie. when the header is shown and scroll != 0).
    expect(Math.round(parseFloat(title.style.top) - wrapwrap.getBoundingClientRect().top)).toBe(HEADER_SIZE + DEFAULT_OFFSET)
    await customScroll(wrapwrap, 0, 40);
    expect(Math.round(parseFloat(title.style.top) - wrapwrap.getBoundingClientRect().top)).toBe(HEADER_SIZE + DEFAULT_OFFSET - 40)
    await customScroll(wrapwrap, 40, 200);
    expect(Math.round(parseFloat(title.style.top) - wrapwrap.getBoundingClientRect().top)).toBe(DEFAULT_OFFSET)
    await customScroll(wrapwrap, 200, 400);
    expect(Math.round(parseFloat(title.style.top) - wrapwrap.getBoundingClientRect().top)).toBe(HEADER_SIZE + DEFAULT_OFFSET - 400)
    await customScroll(wrapwrap, 400, 200);
    expect(Math.round(parseFloat(title.style.top) - wrapwrap.getBoundingClientRect().top)).toBe(DEFAULT_OFFSET)
    await customScroll(wrapwrap, 200, 40);
    expect(Math.round(parseFloat(title.style.top) - wrapwrap.getBoundingClientRect().top)).toBe(HEADER_SIZE + DEFAULT_OFFSET - 40)
    await customScroll(wrapwrap, 40, 0);
    expect(Math.round(parseFloat(title.style.top) - wrapwrap.getBoundingClientRect().top)).toBe(HEADER_SIZE + DEFAULT_OFFSET)
});

test.tags("desktop")("faq_horizontal updates titles position with a o_header_fixed", async () => {
    const { el, core } = await startInteractions(getTemplate("o_header_fixed", false));
    expect(core.interactions.length).toBe(2);
    const wrapwrap = el.querySelector("#wrapwrap");
    const title = el.querySelector(".s_faq_horizontal_entry_title");
    await setupTest(core, wrapwrap);
    // Since the header does not move in Hoot, the first scroll we do
    // create a scroll offset we have to take into account when checking
    // where the bottom of the header is (ie. when the header is shown
    // and scroll != 0).
    //
    // TODO Investigate where this issue comes from (might be like to
    // the fact the state "atTop" is updated and there is a transform
    // applied to the header).
    const offset = 10;
    expect(Math.round(parseFloat(title.style.top) - wrapwrap.getBoundingClientRect().top)).toBe(HEADER_SIZE + DEFAULT_OFFSET)
    await customScroll(wrapwrap, 0, offset);
    document.dispatchEvent(new Event("scroll"));
    expect(Math.round(parseFloat(title.style.top) - wrapwrap.getBoundingClientRect().top)).toBe(HEADER_SIZE + DEFAULT_OFFSET - offset)
    await customScroll(wrapwrap, offset, 15);
    expect(Math.round(parseFloat(title.style.top) - wrapwrap.getBoundingClientRect().top)).toBe(HEADER_SIZE + DEFAULT_OFFSET - offset)
    await customScroll(wrapwrap, 15, 400);
    expect(Math.round(parseFloat(title.style.top) - wrapwrap.getBoundingClientRect().top)).toBe(HEADER_SIZE + DEFAULT_OFFSET - offset)
    await customScroll(wrapwrap, 400, 15);
    expect(Math.round(parseFloat(title.style.top) - wrapwrap.getBoundingClientRect().top)).toBe(HEADER_SIZE + DEFAULT_OFFSET - offset)
    await customScroll(wrapwrap, 15, 0);
    expect(Math.round(parseFloat(title.style.top) - wrapwrap.getBoundingClientRect().top)).toBe(HEADER_SIZE + DEFAULT_OFFSET)
});

test.tags("desktop")("faq_horizontal updates titles position with a o_header_disappears", async () => {
    const { el, core } = await startInteractions(getTemplate("o_header_disappears", false));
    expect(core.interactions.length).toBe(2);
    const wrapwrap = el.querySelector("#wrapwrap");
    const title = el.querySelector(".s_faq_horizontal_entry_title");
    await setupTest(core, wrapwrap);
    // Since the header does not move in Hoot, we have to take into
    // account the scroll in the test when checking where the bottom
    // of the header is (ie. when the header is shown and scroll != 0).
    expect(Math.round(parseFloat(title.style.top) - wrapwrap.getBoundingClientRect().top)).toBe(HEADER_SIZE + DEFAULT_OFFSET);
    await customScroll(wrapwrap, 0, 10);
    expect(Math.round(parseFloat(title.style.top) - wrapwrap.getBoundingClientRect().top)).toBe(HEADER_SIZE + DEFAULT_OFFSET - 10)
    await customScroll(wrapwrap, 10, 400);
    expect(Math.round(parseFloat(title.style.top) - wrapwrap.getBoundingClientRect().top)).toBe(DEFAULT_OFFSET)
    await customScroll(wrapwrap, 400, 15);
    expect(Math.round(parseFloat(title.style.top) - wrapwrap.getBoundingClientRect().top)).toBe(HEADER_SIZE + DEFAULT_OFFSET - 15)
    await customScroll(wrapwrap, 15, 0);
    expect(Math.round(parseFloat(title.style.top) - wrapwrap.getBoundingClientRect().top)).toBe(HEADER_SIZE + DEFAULT_OFFSET)
});

test.tags("desktop")("faq_horizontal updates titles position with a o_header_fade_out", async () => {
    const { el, core } = await startInteractions(getTemplate("o_header_fade_out", false));
    expect(core.interactions.length).toBe(2);
    const wrapwrap = el.querySelector("#wrapwrap");
    const title = el.querySelector(".s_faq_horizontal_entry_title");
    console.log(wrapwrap.getBoundingClientRect().top);
    await setupTest(core, wrapwrap);
    // Since the header does not move in Hoot, we have to take into
    // account the scroll in the test when checking where the bottom
    // of the header is (ie. when the header is shown and scroll != 0).
    expect(Math.round(parseFloat(title.style.top) - wrapwrap.getBoundingClientRect().top)).toBe(HEADER_SIZE + DEFAULT_OFFSET);
    await customScroll(wrapwrap, 0, 10);
    expect(Math.round(parseFloat(title.style.top) - wrapwrap.getBoundingClientRect().top)).toBe(HEADER_SIZE + DEFAULT_OFFSET - 10)
    await customScroll(wrapwrap, 10, 400);
    expect(Math.round(parseFloat(title.style.top) - wrapwrap.getBoundingClientRect().top)).toBe(DEFAULT_OFFSET);
    await customScroll(wrapwrap, 400, 15);
    await animationFrame();
    expect(Math.round(parseFloat(title.style.top) - wrapwrap.getBoundingClientRect().top)).toBe(HEADER_SIZE + DEFAULT_OFFSET - 15)
    await customScroll(wrapwrap, 15, 0);
    expect(Math.round(parseFloat(title.style.top) - wrapwrap.getBoundingClientRect().top)).toBe(HEADER_SIZE + DEFAULT_OFFSET)
});
