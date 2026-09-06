import { expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { contains, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";
import { dummyBase64Img } from "@html_builder/../tests/helpers";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { LcpMarkingPlugin } from "@website/builder/plugins/lcp_marking_plugin";

defineWebsiteModels();

const originalElectImageUrl = LcpMarkingPlugin.prototype.electImageUrl;

function trackRpcs(assertSave) {
    const written = [];
    let notifySaved;
    const saved = new Promise((resolve) => (notifySaved = resolve));
    onRpc("ir.ui.view", "write", ({ args, kwargs }) => {
        expect(kwargs.context.website_id).toBe(1);
        written.push(args[1]);
        return true;
    });
    onRpc("ir.ui.view", "save", ({ args }) => {
        assertSave?.(new DOMParser().parseFromString(args[1], "text/html"));
        expect.step("save");
        notifySaved();
        return true;
    });
    return { written, saved };
}

let measured;
let notifyMeasured;

function patchLcp(overrides) {
    measured = new Promise((resolve) => (notifyMeasured = resolve));
    patchWithCleanup(LcpMarkingPlugin.prototype, {
        electImageUrl: originalElectImageUrl,
        lcpRecord() {
            return { model: "ir.ui.view", id: 1 };
        },
        async saveLcpImages(...args) {
            const result = await super.saveLcpImages(...args);
            notifyMeasured();
            return result;
        },
        ...overrides,
    });
}

function electUrl(pick) {
    patchLcp({
        async electImageUrl(viewport) {
            return pick(viewport);
        },
    });
}

function electEntry(pick) {
    patchLcp({
        async observeLcpEntry(win) {
            return pick(win);
        },
    });
}

async function dirtyAndSave(getEditor) {
    const paragraphEl = queryOne(":iframe .edit-me");
    setSelection({ anchorNode: paragraphEl.firstChild, anchorOffset: 1 });
    await insertText(getEditor(), "x");
    await contains(".o-snippets-top-actions button:contains(Save)").click();
}

test("the elected url is stored for each device", async () => {
    const { written, saved } = trackRpcs();
    const { getEditor } = await setupWebsiteBuilder(`
        <section>
            <img class="hero" style="width: 800px; height: 400px;" src='${dummyBase64Img}'/>
            <p class="edit-me">edit</p>
        </section>
    `);
    electUrl((viewport) => (viewport.width > 992 ? "/web/image/1" : "/web/image/2"));
    await dirtyAndSave(getEditor);
    await measured;
    await saved;
    expect.verifySteps(["save"]);
    expect(written).toEqual([
        { website_lcp_image_desktop: "/web/image/1", website_lcp_image_mobile: "/web/image/2" },
    ]);
});

test("an entry that is not an image clears the url of its device", async () => {
    const { written, saved } = trackRpcs();
    const { getEditor } = await setupWebsiteBuilder(`
        <section>
            <h1>Hero title</h1>
            <p class="edit-me">edit</p>
        </section>
    `);
    electUrl((viewport) => (viewport.width > 992 ? false : "/web/image/2"));
    await dirtyAndSave(getEditor);
    await measured;
    await saved;
    expect.verifySteps(["save"]);
    expect(written).toEqual([
        { website_lcp_image_desktop: false, website_lcp_image_mobile: "/web/image/2" },
    ]);
});

test("restricted editors do not save LCP image hints", async () => {
    onRpc("has_group", ({ args }) => args[1] !== "website.group_website_designer");
    const { written, saved } = trackRpcs();
    const { getEditor } = await setupWebsiteBuilder(`
        <section>
            <img style="width: 800px; height: 400px;" src='${dummyBase64Img}'/>
            <p class="edit-me">edit</p>
        </section>
    `);
    await dirtyAndSave(getEditor);
    await saved;
    expect.verifySteps(["save"]);
    expect(written).toEqual([]);
});

test("nothing is written when no entry is measured", async () => {
    const { saved } = trackRpcs();
    const { getEditor } = await setupWebsiteBuilder(`
        <section>
            <p class="edit-me">edit</p>
        </section>
    `);
    electUrl(() => undefined);
    await dirtyAndSave(getEditor);
    await measured;
    await saved;
    expect.verifySteps(["save"]);
});

test("the url of the elected image is read from its src", async () => {
    const { written, saved } = trackRpcs();
    const { getEditor } = await setupWebsiteBuilder(`
        <section>
            <img class="target" style="width: 800px; height: 400px;" src="/web/image/7"/>
            <p class="edit-me">edit</p>
        </section>
    `);
    electEntry((win) => win.document.querySelector(".target"));
    await dirtyAndSave(getEditor);
    await measured;
    await saved;
    expect.verifySteps(["save"]);
    expect(written).toEqual([
        { website_lcp_image_desktop: "/web/image/7", website_lcp_image_mobile: "/web/image/7" },
    ]);
});

test("an uploaded image field is stored with its rendered url on the first save", async () => {
    const renderedUrl = "/web/image/product.product/12/image_1920/Product?unique=old";
    const uploadedUrl = "/web/static/img/logo2.png";
    const { written, saved } = trackRpcs((doc) => {
        const imageEl = doc.querySelector("[data-oe-type='image'] img");
        expect(imageEl).not.toBe(null);
        expect(imageEl).not.toHaveAttribute("data-lcp-image-field-src");
    });
    onRpc("ir.attachment", "search_read", () => [
        {
            id: 1,
            name: "Product",
            mimetype: "image/png",
            image_src: uploadedUrl,
            access_token: false,
            public: true,
        },
    ]);
    onRpc("/html_editor/get_image_info", () => ({
        original: { id: 1, image_src: uploadedUrl, mimetype: "image/png" },
    }));
    onRpc("/html_editor/modify_image/1", () => ({ original: uploadedUrl }));
    const { getEditor, waitSidebarUpdated } = await setupWebsiteBuilder(`
        <section>
            <div data-oe-model="product.product" data-oe-id="12"
                data-oe-field="image_1920" data-oe-type="image"
                data-oe-expression="product_image.image_1920">
                <img src="${renderedUrl}"/>
            </div>
        </section>
    `);
    await contains(":iframe [data-oe-type='image'] img").click();
    await waitSidebarUpdated();
    await contains("[data-action-id=replaceMedia]").click();
    await contains(".o_existing_attachment_cell .o_button_area").click();
    await waitSidebarUpdated();
    expect(":iframe [data-oe-type='image'] img").toHaveAttribute(
        "data-lcp-image-field-src",
        renderedUrl
    );
    expect(":iframe [data-oe-type='image'] img").toHaveAttribute("data-original-id", "1");
    const firstImageEl = getEditor().editable.querySelector("[data-oe-type='image'] img");
    const secondImageEl = firstImageEl.cloneNode();
    secondImageEl.removeAttribute("data-lcp-image-field-src");
    const lcpPlugin = getEditor().plugins.find((plugin) => plugin.constructor === LcpMarkingPlugin);
    lcpPlugin.preserveImageFieldSrc([secondImageEl], { node: firstImageEl });
    firstImageEl.parentElement.replaceChild(secondImageEl, firstImageEl);
    expect(secondImageEl).toHaveAttribute("data-lcp-image-field-src", renderedUrl);
    patchLcp({
        electImageUrl(viewport, snapshot) {
            const imageEl = snapshot.editableCloneEl.querySelector("[data-oe-type='image'] img");
            expect(imageEl).toHaveAttribute("src", uploadedUrl);
            return this.imageUrl(imageEl);
        },
    });
    await getEditor().shared.savePlugin.save();
    await measured;
    await saved;
    expect.verifySteps(["save"]);
    expect(written).toEqual([
        {
            website_lcp_image_desktop: renderedUrl,
            website_lcp_image_mobile: renderedUrl,
        },
    ]);
});

test("the snapshot waits for pending image saves", async () => {
    const { written, saved } = trackRpcs();
    onRpc("/html_editor/modify_image/308", () => ({
        original: "/web/image/309-abc123/hero.webp",
    }));
    const { getEditor } = await setupWebsiteBuilder(`
        <section>
            <img class="target o_modified_image_to_save" data-original-id="308" style="width: 300px; height: 200px;" src='${dummyBase64Img}'/>
            <p class="edit-me">edit</p>
        </section>
    `);
    electEntry((win) => win.document.querySelector(".target"));
    await dirtyAndSave(getEditor);
    await measured;
    await saved;
    expect.verifySteps(["save"]);
    expect(written).toEqual([
        {
            website_lcp_image_desktop: "/web/image/309-abc123/hero.webp",
            website_lcp_image_mobile: "/web/image/309-abc123/hero.webp",
        },
    ]);
});

test("render-injected priority attributes are stripped on save", async () => {
    const { saved } = trackRpcs((doc) => {
        const marked = doc.querySelector(".marked");
        expect(marked.getAttribute("loading")).toBe(null);
        expect(marked.getAttribute("fetchpriority")).toBe(null);
        expect(doc.querySelector(".keep").getAttribute("loading")).toBe("eager");
        const embedded = doc.querySelector(".s_embed_code img");
        expect(embedded.getAttribute("loading")).toBe(null);
        expect(embedded.getAttribute("fetchpriority")).toBe(null);
    });
    const { getEditor } = await setupWebsiteBuilder(`
        <section>
            <img class="marked" loading="eager" fetchpriority="high" style="width: 300px; height: 200px;" src='${dummyBase64Img}'/>
            <img class="keep" loading="eager" style="width: 50px; height: 50px;" src='${dummyBase64Img}'/>
            <div class="s_embed_code">
                <img loading="eager" fetchpriority="high" style="width: 50px; height: 50px;" src='${dummyBase64Img}'/>
            </div>
            <p class="edit-me">edit</p>
        </section>
    `);
    electUrl(() => undefined);
    await dirtyAndSave(getEditor);
    await measured;
    await saved;
    expect.verifySteps(["save"]);
});

test("the measurement frame is painted at the device viewport", async () => {
    const measured = [];
    let notifyMeasured;
    const measuredBothViewports = new Promise((resolve) => (notifyMeasured = resolve));
    const { saved } = trackRpcs();
    const { getEditor } = await setupWebsiteBuilder(`
        <section>
            <img class="target" style="width: 800px; height: 400px;" src='${dummyBase64Img}'/>
            <p class="edit-me">edit</p>
        </section>
    `);
    patchWithCleanup(LcpMarkingPlugin.prototype, {
        electImageUrl: originalElectImageUrl,
        lcpRecord() {
            return { model: "ir.ui.view", id: 1 };
        },
        async appendMeasureFrame(viewport) {
            const frame = await super.appendMeasureFrame(viewport);
            const frameRect = frame.iframeEl.getBoundingClientRect();
            const hostRect = frame.hostEl.getBoundingClientRect();
            measured.push({
                viewport: `${viewport.width}x${viewport.height}`,
                clipped: hostRect.width < frameRect.width || hostRect.height < frameRect.height,
                outsideViewport:
                    frameRect.right > window.innerWidth + 1 ||
                    frameRect.bottom > window.innerHeight + 1,
                reachableBySelectors: [...document.getElementsByTagName("iframe")].includes(
                    frame.iframeEl
                ),
            });
            if (measured.length === 2) {
                notifyMeasured();
            }
            return frame;
        },
        async observeLcpEntry() {
            return undefined;
        },
    });
    await dirtyAndSave(getEditor);
    await measuredBothViewports;
    await saved;
    expect.verifySteps(["save"]);
    expect(measured.map((m) => m.viewport).sort()).toEqual(["1199x768", "991x667"]);
    expect(measured.map((m) => m.clipped)).toEqual([false, false]);
    expect(measured.map((m) => m.outsideViewport)).toEqual([false, false]);
    expect(measured.map((m) => m.reachableBySelectors)).toEqual([false, false]);
});
