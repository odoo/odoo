import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { queryFirst, queryOne } from "@odoo/hoot-dom";

import { setupTest, simpleScroll, doubleScroll } from "./helpers";

setupInteractionWhiteList([
    "website.header_standard",
    "website.header_fixed",
    "website.header_disappears",
    "website.header_fade_out",
    "website.faq_horizontal",
]);

describe.current.tags("interaction_dev");

const getTemplate = function (headerType) {
    return `
        <header class="${headerType}" style="background-color:#CCFFCC">
            <div style="height: 50px; background-color:#33FFCC;"></div>
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
                            <img src="/web/image/website.s_faq_horizontal_default_image_1" class="img img-fluid rounded" style="width: 100% !important;" alt="" loading="lazy" data-mimetype="image/webp" data-attachment-id="278" data-original-id="278" data-original-src="/website/static/src/img/snippets_demo/s_faq_horizontal_1.webp" data-mimetype-before-conversion="image/webp">
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
    `;
};

const HEADER_SIZE = 50;
const DEFAULT_OFFSET = 16;

const SCROLLS = [0, 40, 250, 400, 250, 40, 0];
const SCROLLS_SPECIAL = [0, 40, 400, 40, 0];

test("faq_horizontal is started when there is an element .s_faq_horizontal", async () => {
    const { core } = await startInteractions(getTemplate(""));
    expect(core.interactions).toHaveLength(1);
});

test.tags("desktop");
test("faq_horizontal updates titles position with a o_header_standard", async () => {
    const { core } = await startInteractions(getTemplate("o_header_standard"));
    expect(core.interactions).toHaveLength(2);
    const wrapwrap = queryOne("#wrapwrap");
    const title = queryFirst(".s_faq_horizontal_entry_title");
    await setupTest(core, wrapwrap);
    for (const target of SCROLLS) {
        await simpleScroll(wrapwrap, target);
        const calculatedTop = Math.round(parseFloat(title.style.top));
        const isHeaderVisible = target < HEADER_SIZE || target > 300;
        // We compensate the scroll since the header does not move in Hoot.
        const correctedTop = isHeaderVisible ? calculatedTop + target : calculatedTop;
        expect(correctedTop).toBe(isHeaderVisible ? HEADER_SIZE + DEFAULT_OFFSET : DEFAULT_OFFSET);
    }
});

test.tags("desktop");
test("faq_horizontal updates titles position with a o_header_fixed", async () => {
    const { core } = await startInteractions(getTemplate("o_header_fixed"));
    expect(core.interactions).toHaveLength(2);
    // We force the header to never be consider "atTop", so that its
    // position is properly computed.
    core.interactions[0].interaction.topGap = -1;
    const wrapwrap = queryOne("#wrapwrap");
    const title = queryFirst(".s_faq_horizontal_entry_title");
    await setupTest(core, wrapwrap);
    for (const target of SCROLLS_SPECIAL) {
        await simpleScroll(wrapwrap, target);
        // There is no need to compensate the scroll here
        expect(Math.round(parseFloat(title.style.top))).toBe(HEADER_SIZE + DEFAULT_OFFSET);
    }
});

test.tags("desktop");
test("faq_horizontal updates titles position with a o_header_disappears", async () => {
    const { core } = await startInteractions(getTemplate("o_header_disappears"));
    expect(core.interactions).toHaveLength(2);
    const wrapwrap = queryOne("#wrapwrap");
    const title = queryFirst(".s_faq_horizontal_entry_title");
    await setupTest(core, wrapwrap);
    for (let i = 1; i < SCROLLS_SPECIAL.length; i++) {
        const target = SCROLLS_SPECIAL[i];
        const source = SCROLLS_SPECIAL[i - 1];
        await doubleScroll(wrapwrap, target, source);
        const calculatedTop = Math.round(parseFloat(title.style.top));
        const isHeaderVisible = target < 300;
        // We compensate the scroll since the header does not move in Hoot.
        const correctedTop = isHeaderVisible ? calculatedTop + target : calculatedTop;
        expect(correctedTop).toBe(isHeaderVisible ? HEADER_SIZE + DEFAULT_OFFSET : DEFAULT_OFFSET);
    }
});

test.tags("desktop");
test("faq_horizontal updates titles position with a o_header_fade_out", async () => {
    const { core } = await startInteractions(getTemplate("o_header_fade_out"));
    expect(core.interactions).toHaveLength(2);
    const wrapwrap = queryOne("#wrapwrap");
    const title = queryFirst(".s_faq_horizontal_entry_title");
    await setupTest(core, wrapwrap);
    for (let i = 1; i < SCROLLS_SPECIAL.length; i++) {
        const target = SCROLLS_SPECIAL[i];
        const source = SCROLLS_SPECIAL[i - 1];
        await doubleScroll(wrapwrap, target, source);
        const calculatedTop = Math.round(parseFloat(title.style.top));
        const isHeaderVisible = target < 300;
        // We compensate the scroll since the header does not move in Hoot.
        const correctedTop = isHeaderVisible ? calculatedTop + target : calculatedTop;
        expect(correctedTop).toBe(isHeaderVisible ? HEADER_SIZE + DEFAULT_OFFSET : DEFAULT_OFFSET);
    }
});
