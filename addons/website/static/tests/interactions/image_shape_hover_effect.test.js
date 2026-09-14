import "@website/interactions/image_shape_hover_effect.edit";

import { describe, expect, test } from "@odoo/hoot";
import { hover, queryOne } from "@odoo/hoot-dom";
import { advanceTime, mockFetch, tick } from "@odoo/hoot-mock";
import {
    setupInteractionWhiteList,
    startInteractions,
} from "@web/../tests/public/helpers";
import { onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { Deferred } from "@web/core/utils/concurrency";
import { ImageShapeHoverEffect } from "@website/interactions/image_shape_hover_effect";
import { onceAllImagesLoaded } from "@website/utils/images";

setupInteractionWhiteList("website.image_shape_hover_effect");

describe.current.tags("interaction_dev");

test("a failed SVG fetch releases the queue and allows another hover", async () => {
    const { core } = await startInteractions(
        `<img src="data:image/svg+xml,%3Csvg/%3E" data-hover-effect="zoom"/>`,
    );
    const interaction = core.interactions[0].interaction;
    mockFetch(() => {
        expect.step("fetch");
        throw new Error("network unavailable");
    });
    interaction.mouseEnter();
    await tick();
    interaction.mouseLeave();
    interaction.mouseEnter();
    await tick();
    expect.verifySteps(["fetch", "fetch"]);
});

test("destroyed hover interactions release pending source changes", () => {
    ImageShapeHoverEffect.prototype.setImgSrc.call({ isDestroyed: true }, null, () =>
        expect.step("settled"),
    );
    expect.verifySteps(["settled"]);
});

test("a failed SVG preload releases the hover queue", async () => {
    const { core } = await startInteractions(
        `<img src="data:image/svg+xml,%3Csvg/%3E" data-hover-effect="zoom"/>`,
    );
    const interaction = core.interactions[0].interaction;
    let preload;
    patchWithCleanup(window, {
        Image: class extends EventTarget {
            constructor() {
                super();
                preload = this;
            }
            set src(value) {}
        },
    });
    const svg = new DOMParser().parseFromString(
        '<svg xmlns="http://www.w3.org/2000/svg"/>',
        "text/xml",
    ).documentElement;
    interaction.setImgSrc(svg, () => expect.step("settled"));
    preload.onerror?.();
    preload.dispatchEvent(new Event("error"));
    expect.verifySteps(["settled"]);
});

test("destroying an interaction settles a pending SVG preload", async () => {
    const { core } = await startInteractions(
        '<img src="data:image/svg+xml,%3Csvg/%3E" data-hover-effect="zoom"/>',
    );
    const interaction = core.interactions[0].interaction;
    patchWithCleanup(window, {
        Image: class extends EventTarget {
            set src(value) {}
        },
    });
    const svg = new DOMParser().parseFromString(
        '<svg xmlns="http://www.w3.org/2000/svg"/>',
        "text/xml",
    ).documentElement;
    let settled = false;
    interaction.setImgSrc(svg, () => {
        settled = true;
    });
    core.stopInteractions();
    await tick();
    expect(settled).toBe(true);
});

test("source changes preserve existing image load and error handlers", async () => {
    const { core } = await startInteractions(
        '<img src="data:image/svg+xml,%3Csvg/%3E" data-hover-effect="zoom"/>',
    );
    const interaction = core.interactions[0].interaction;
    const onLoad = () => {};
    const onError = () => {};
    interaction.el.onload = onLoad;
    interaction.el.onerror = onError;
    let preload;
    patchWithCleanup(window, {
        Image: class extends EventTarget {
            constructor() {
                super();
                preload = this;
            }
            set src(value) {
                this.value = value;
            }
            getAttribute() {
                return this.value;
            }
        },
    });
    const svg = new DOMParser().parseFromString(
        '<svg xmlns="http://www.w3.org/2000/svg"/>',
        "text/xml",
    ).documentElement;
    interaction.setImgSrc(svg, () => {});
    preload.onload?.();
    preload.dispatchEvent(new Event("load"));
    expect(interaction.el.onload).toBe(onLoad);
    expect(interaction.el.onerror).toBe(onError);
});

test("an external src edit invalidates both cached hover directions", async () => {
    const { core } = await startInteractions(
        '<img src="data:image/svg+xml,%3Csvg/%3E" data-hover-effect="zoom"/>',
    );
    const interaction = core.interactions[0].interaction;
    interaction.svgInEl = document.createElement("svg");
    interaction.svgOutEl = document.createElement("svg");
    interaction.el.setAttribute("src", "data:image/svg+xml,%3Csvg%20id='new'/%3E");
    await tick();
    expect(interaction.svgInEl).toBe(null);
    expect(interaction.svgOutEl).toBe(null);
});

test("an old SVG response cannot replace an edited image", async () => {
    const { core } = await startInteractions(
        '<img src="data:image/svg+xml,%3Csvg/%3E" data-hover-effect="zoom"/>',
    );
    const interaction = core.interactions[0].interaction;
    const response = new Deferred();
    mockFetch(() => response);
    patchWithCleanup(interaction, {
        setImgSrc(svg, resolve) {
            expect.step("stale image applied");
            resolve();
        },
    });
    interaction.mouseEnter();
    await tick();
    interaction.el.setAttribute("src", "data:image/svg+xml,%3Csvg%20id='new'/%3E");
    await tick();
    response.resolve(new Response('<svg xmlns="http://www.w3.org/2000/svg"/>'));
    await interaction.lastMouseEvent;
    expect.verifySteps([]);
    expect(interaction.svgInEl).toBe(null);
});

test("destruction releases a hover waiting for an SVG response", async () => {
    const { core } = await startInteractions(
        '<img src="data:image/svg+xml,%3Csvg/%3E" data-hover-effect="zoom"/>',
    );
    const interaction = core.interactions[0].interaction;
    mockFetch(() => new Deferred());
    interaction.mouseEnter();
    let settled = false;
    interaction.lastMouseEvent.then(() => {
        settled = true;
    });
    await tick();
    core.stopInteractions();
    await tick();
    expect(settled).toBe(true);
});

test("destruction preserves an external src edit before observer delivery", async () => {
    const { core } = await startInteractions(
        '<img src="data:image/svg+xml,%3Csvg/%3E" data-hover-effect="zoom"/>',
    );
    const interaction = core.interactions[0].interaction;
    const edited = "data:image/svg+xml,%3Csvg%20id='new'/%3E";
    interaction.el.setAttribute("src", edited);
    core.stopInteractions();
    expect(interaction.el).toHaveAttribute("src", edited);
});

test("outgoing SVGs reverse from/to animations without a values attribute", async () => {
    const { core } = await startInteractions(
        '<img src="data:image/svg+xml,%3Csvg/%3E" data-hover-effect="zoom"/>',
    );
    const interaction = core.interactions[0].interaction;
    interaction.svgInEl = new DOMParser().parseFromString(
        '<svg xmlns="http://www.w3.org/2000/svg"><g id="hoverEffects"><animate from="0" to="1"/></g></svg>',
        "text/xml",
    ).documentElement;
    patchWithCleanup(interaction, {
        setImgSrc(svg, resolve) {
            resolve();
        },
    });
    interaction.mouseLeave();
    await interaction.lastMouseEvent;
    expect(interaction.svgOutEl.querySelector("animate").hasAttribute("values")).toBe(
        false,
    );
    expect(interaction.svgOutEl.querySelector("animate")).toHaveAttribute("from", "1");
    expect(interaction.svgOutEl.querySelector("animate")).toHaveAttribute("to", "0");
});

function useEditorHover() {
    const { mixin } = registry
        .category("public.interactions.edit")
        .get("website.image_shape_hover_effect");
    registry
        .category("public.interactions")
        .add("website.image_shape_hover_effect", mixin(ImageShapeHoverEffect), {
            force: true,
        });
}

test("editor teardown settles its pending reverse-animation timer", async () => {
    useEditorHover();
    const { core } = await startInteractions(
        '<img src="data:image/svg+xml,%3Csvg/%3E" data-hover-effect="zoom"/>',
    );
    const interaction = core.interactions[0].interaction;
    interaction.svgInEl = new DOMParser().parseFromString(
        '<svg xmlns="http://www.w3.org/2000/svg"><g id="hoverEffects"><animate values="0;1" dur="10s"/></g></svg>',
        "text/xml",
    ).documentElement;
    patchWithCleanup(interaction, {
        setImgSrc(svg, resolve) {
            resolve();
        },
    });
    interaction.mouseLeave();
    let settled = false;
    interaction.lastMouseEvent.then(() => {
        settled = true;
    });
    await tick();
    core.stopInteractions();
    await tick();
    expect(settled).toBe(true);
});

test("editor hover restores the original through native image events", async () => {
    useEditorHover();
    const svg =
        '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><g id="hoverEffects"><animate attributeName="opacity" values="0;1" dur="0s"/></g></svg>';
    const original = `data:image/svg+xml,${encodeURIComponent(svg)}`;
    const { core } = await startInteractions(
        `<img src="${original}" data-hover-effect="zoom"/>`,
    );
    const interaction = core.interactions[0].interaction;
    mockFetch(() => new Response(svg));
    const onLoad = () => {};
    const onError = () => {};
    interaction.el.onload = onLoad;
    interaction.el.onerror = onError;
    interaction.mouseEnter();
    await interaction.lastMouseEvent;
    expect(interaction.el.getAttribute("src")).not.toBe(original);
    interaction.mouseLeave();
    // Wait for the reverse image's native load before advancing its zero timer.
    await new Promise((resolve) =>
        interaction.el.addEventListener("load", resolve, { once: true }),
    );
    await tick();
    await advanceTime(0);
    await interaction.lastMouseEvent;
    expect(interaction.el).toHaveAttribute("src", original);
    expect(interaction.el.onload).toBe(onLoad);
    expect(interaction.el.onerror).toBe(onError);
});

test("a stale preload cannot overwrite a new image source", async () => {
    const { core } = await startInteractions(
        '<img src="data:image/svg+xml,%3Csvg/%3E" data-hover-effect="zoom"/>',
    );
    const interaction = core.interactions[0].interaction;
    let preload;
    patchWithCleanup(window, {
        Image: class extends EventTarget {
            constructor() {
                super();
                preload = this;
            }
            set src(value) {
                this.value = value;
            }
            getAttribute() {
                return this.value;
            }
        },
    });
    let settled = false;
    interaction.setImageSource("old image", () => {
        settled = true;
    });
    const edited = "data:image/svg+xml,%3Csvg%20id='new'/%3E";
    interaction.el.setAttribute("src", edited);
    await tick();
    preload.dispatchEvent(new Event("load"));
    expect(interaction.el).toHaveAttribute("src", edited);
    expect(settled).toBe(true);
});

test("editing the source cancels an editor's delayed restore", async () => {
    useEditorHover();
    const { core } = await startInteractions(
        '<img src="data:image/svg+xml,%3Csvg/%3E" data-hover-effect="zoom"/>',
    );
    const interaction = core.interactions[0].interaction;
    interaction.svgInEl = new DOMParser().parseFromString(
        '<svg xmlns="http://www.w3.org/2000/svg"><g id="hoverEffects"><animate values="0;1" dur="10s"/></g></svg>',
        "text/xml",
    ).documentElement;
    patchWithCleanup(interaction, {
        setImgSrc(svg, resolve) {
            resolve();
        },
    });
    interaction.mouseLeave();
    await tick();
    const edited = "data:image/svg+xml,%3Csvg%20id='new'/%3E";
    interaction.el.setAttribute("src", edited);
    await tick();
    await interaction.lastMouseEvent;
    await advanceTime(10000);
    expect(interaction.el).toHaveAttribute("src", edited);
});

test.tags("desktop");
test("image_shape_hover_effect changes image on enter & leave", async () => {
    onRpc(
        "/web/image/384-8a55a748/s_banner_3.svg",
        () =>
            `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 100" width="500px"><g id="hoverEffects"><animate values="a=1;b=2"><rect width="100%" fill="red" height="100%" /></animate></g></svg>`,
    );
    const { core } = await startInteractions(`
        <div id="wrapwrap">
            <img class="img img-fluid mx-auto o_we_image_cropped o_animate_on_hover rounded-circle rounded"
                src="/web/image/384-8a55a748/s_banner_3.svg" alt=""
                data-mimetype="image/svg+xml" data-attachment-id="276" data-original-id="276"
                data-original-src="/website/static/src/img/snippets_demo/s_banner_3.jpg"
                data-mimetype-before-conversion="image/jpeg"
                data-shape="html_builder/geometric/geo_door" data-file-name="s_banner_3.svg"
                data-shape-colors=";;;;" data-format-mimetype="image/jpeg"
                data-x="160" data-y="0"
                data-width="640" data-height="640"
                data-scale-x="1" data-scale-y="1"
                data-aspect-ratio="1/1"
                data-hover-effect="dolly_zoom"
                data-hover-effect-color="rgba(0, 0, 0, 0)"
                data-hover-effect-intensity="20"/>
            <div class="not_image">Not the image</div>
        </div>
    `);
    expect(core.interactions).toHaveLength(1);
    await onceAllImagesLoaded(queryOne("#wrapwrap")).catch(() => {});
    const imgEl = queryOne("img");
    const baseSrc = imgEl.getAttribute("src");
    expect(imgEl).toHaveAttribute("src", "/web/image/384-8a55a748/s_banner_3.svg");
    await hover(imgEl);
    await core.interactions[0].interaction.lastMouseEvent;
    const altSrc = imgEl.getAttribute("src");
    expect(imgEl).not.toHaveAttribute("src", baseSrc);
    await hover(".not_image");
    await core.interactions[0].interaction.lastMouseEvent;
    expect(imgEl).not.toHaveAttribute("src", baseSrc);
    expect(imgEl).not.toHaveAttribute("src", altSrc);
});

test("a source edit between SVG parsing and preload is not overwritten", async () => {
    const { core } = await startInteractions(
        '<img src="data:image/svg+xml,%3Csvg/%3E" data-hover-effect="zoom"/>',
    );
    const interaction = core.interactions[0].interaction;
    const edited = "data:image/svg+xml,%3Csvg%20id='new'/%3E";
    const OriginalParser = window.DOMParser;
    patchWithCleanup(window, {
        DOMParser: class extends OriginalParser {
            parseFromString(...args) {
                const result = super.parseFromString(...args);
                queueMicrotask(() => interaction.el.setAttribute("src", edited));
                return result;
            }
        },
    });
    mockFetch(() => new Response('<svg xmlns="http://www.w3.org/2000/svg"/>'));
    patchWithCleanup(interaction, {
        setImgSrc(svg, resolve) {
            expect.step("obsolete SVG applied");
            resolve();
        },
    });
    interaction.mouseEnter();
    await interaction.lastMouseEvent;
    expect.verifySteps([]);
    expect(interaction.el).toHaveAttribute("src", edited);
});
