import { describe, expect, getFixture, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import {
    contains,
    getService,
    mockService,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { lcpMeasurement } from "@website/components/dialog/lcp_measurement_utils";
import { OptimizeSEODialog } from "@website/components/dialog/seo";
import { defineWebsiteModels } from "./builder/website_helpers";

defineWebsiteModels();

const SEO_TITLE = "Title";
const seoData = {
    lang: { code: "en_US", name: "English (US)" },
    multi_lang: false,
    default_lang_code: "en_US",
    can_edit_seo: true,
    website_meta_og_img: false,
    website_meta_title: SEO_TITLE,
    website_meta_description: "Description",
    website_meta_keywords: "",
    default_website_meta_title: SEO_TITLE,
    default_website_meta_description: "Description",
    default_website_meta_keywords: "",
    has_social_default_image: false,
};

function pageDocument(bodyHTML) {
    getFixture().append(...new DOMParser().parseFromString(bodyHTML, "text/html").body.children);
    return document;
}

async function openSeoDialog(bodyHTML) {
    const written = [];
    const saved = Promise.withResolvers();
    mockService("website", {
        currentWebsite: {
            id: 1,
            metadata: {
                lang: "en_US",
                mainObject: { model: "website.page", id: 4 },
                seoObject: { model: "ir.ui.view", id: 1 },
                path: "http://localhost/",
            },
        },
        pageDocument: pageDocument(bodyHTML),
        goToWebsite() {
            saved.resolve();
        },
    });
    onRpc("/website/get_seo_data", () => seoData);
    onRpc("/website/get_languages", () => [["en_US", "English (US)", "en_US"]]);
    onRpc("/website/get_alt_images", () => "[]");
    onRpc("ir.ui.view", "write", ({ args, kwargs }) => {
        expect(kwargs.context).toMatchObject({ lang: "en_US", website_id: 1 });
        written.push(args);
        return true;
    });
    await mountWithCleanup(MainComponentsContainer);
    getService("dialog").add(OptimizeSEODialog, {});
    await waitFor(".oe_seo_configuration");
    return {
        written,
        async save() {
            await contains(".modal-footer .btn-primary").click();
            await saved.promise;
        },
    };
}

describe("LCP hints on SEO save", () => {
    test("the elected image of each device is saved with the SEO data", async () => {
        patchWithCleanup(lcpMeasurement, {
            observeLcpEntry: (win) => win.document.querySelector("img"),
        });
        const { written, save } = await openSeoDialog(`
            <div id="wrapwrap">
                <img src="/web/image/7?unique=abc" style="width: 800px; height: 400px;"/>
            </div>
        `);
        await save();
        expect(written).toHaveLength(1);
        expect(written[0][0]).toEqual([1]);
        expect(written[0][1]).toMatchObject({
            website_meta_title: SEO_TITLE,
            website_lcp_image_desktop: "/web/image/7?unique=abc",
            website_lcp_image_mobile: "/web/image/7?unique=abc",
        });
    });

    test("a device whose largest paint is not an image clears its hint", async () => {
        patchWithCleanup(lcpMeasurement, {
            electImageUrl: async (viewportSize) =>
                viewportSize.width > 992 ? false : "/web/image/2",
        });
        const { written, save } = await openSeoDialog(
            `<div id="wrapwrap"><h1>Hero title</h1></div>`
        );
        await save();
        expect(written[0][1]).toMatchObject({
            website_lcp_image_desktop: false,
            website_lcp_image_mobile: "/web/image/2",
        });
    });

    test("no hint is written for a device that could not be measured", async () => {
        patchWithCleanup(lcpMeasurement, {
            observeLcpEntry: async () => undefined,
        });
        const { written, save } = await openSeoDialog(`<div id="wrapwrap"><p>text</p></div>`);
        await save();
        expect(written).toHaveLength(1);
        expect(written[0][1]).toMatchObject({ website_meta_title: SEO_TITLE });
        expect(Object.keys(written[0][1]).filter((key) => key.includes("lcp"))).toEqual([]);
    });

    test("the measurement frames are painted at the device viewport", async () => {
        const measuredFrames = [];
        patchWithCleanup(lcpMeasurement, {
            async appendMeasureFrame(viewportSize) {
                const frame = await super.appendMeasureFrame(viewportSize);
                const frameRect = frame.measurementIframeEl.getBoundingClientRect();
                const hostRect = frame.hostEl.getBoundingClientRect();
                measuredFrames.push({
                    viewport: `${viewportSize.width}x${viewportSize.height}`,
                    clipped: hostRect.width < frameRect.width || hostRect.height < frameRect.height,
                    outsideViewport:
                        frameRect.right > window.innerWidth + 1 ||
                        frameRect.bottom > window.innerHeight + 1,
                    reachableBySelectors: [...document.getElementsByTagName("iframe")].includes(
                        frame.measurementIframeEl
                    ),
                });
                return frame;
            },
            observeLcpEntry: async () => undefined,
        });
        const { save } = await openSeoDialog(`<div id="wrapwrap"><p>text</p></div>`);
        await save();
        expect(measuredFrames.map((m) => m.viewport).sort()).toEqual(["1199x675", "991x1762"]);
        expect(measuredFrames.map((m) => m.clipped)).toEqual([false, false]);
        expect(measuredFrames.map((m) => m.outsideViewport)).toEqual([false, false]);
        expect(measuredFrames.map((m) => m.reachableBySelectors)).toEqual([false, false]);
    });
});
