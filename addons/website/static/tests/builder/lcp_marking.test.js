import { describe, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { contains, getService, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, saveWebsiteBuilder, setupWebsiteBuilder } from "./website_helpers";
import { dummyBase64Img } from "@html_builder/../tests/helpers";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { LcpMarkingPlugin } from "@website/builder/plugins/lcp_marking_plugin";
import { getTranslatedElements } from "./translated_elements_getter.hoot";
import { onRpcImg } from "./image_test_helpers";

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

function patchLcpPlugin(overrides) {
    measured = new Promise((resolve) => (notifyMeasured = resolve));
    patchWithCleanup(LcpMarkingPlugin.prototype, {
        async electImageUrl(...args) {
            return originalElectImageUrl.call(this, ...args);
        },
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

function patchElectImageUrl(electImageUrl) {
    patchLcpPlugin({ electImageUrl });
}

function patchObserveLcpEntry(observeLcpEntry) {
    patchLcpPlugin({ observeLcpEntry });
}

async function dirtyAndSave(getEditor) {
    const paragraphEl = queryOne(":iframe .edit-me");
    setSelection({ anchorNode: paragraphEl.firstChild, anchorOffset: 1 });
    await insertText(getEditor(), "x");
    await contains(".o-snippets-top-actions button:contains(Save)").click();
}

test("the elected url is stored for each device", async () => {
    patchElectImageUrl((viewport) => (viewport.width > 992 ? "/web/image/1" : "/web/image/2"));
    const { written, saved } = trackRpcs();
    const { getEditor } = await setupWebsiteBuilder(`
        <section>
            <img class="hero" style="width: 800px; height: 400px;" src='${dummyBase64Img}'/>
            <p class="edit-me">edit</p>
        </section>
    `);
    await dirtyAndSave(getEditor);
    await Promise.all([measured, saved]);
    expect.verifySteps(["save"]);
    expect(written).toEqual([
        { website_lcp_image_desktop: "/web/image/1", website_lcp_image_mobile: "/web/image/2" },
    ]);
});

test("an entry that is not an image clears the url of its device", async () => {
    patchElectImageUrl((viewport) => (viewport.width > 992 ? false : "/web/image/2"));
    const { written, saved } = trackRpcs();
    const { getEditor } = await setupWebsiteBuilder(`
        <section>
            <h1>Hero title</h1>
            <p class="edit-me">edit</p>
        </section>
    `);
    await dirtyAndSave(getEditor);
    await Promise.all([measured, saved]);
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
    patchElectImageUrl(() => undefined);
    const { saved } = trackRpcs();
    const { getEditor } = await setupWebsiteBuilder(`
        <section>
            <p class="edit-me">edit</p>
        </section>
    `);
    await dirtyAndSave(getEditor);
    await Promise.all([measured, saved]);
    expect.verifySteps(["save"]);
});

test("the url of the elected image is read from its src", async () => {
    patchObserveLcpEntry((win) => win.document.querySelector(".target"));
    const { written, saved } = trackRpcs();
    const { getEditor } = await setupWebsiteBuilder(`
        <section>
            <img class="target" style="width: 800px; height: 400px;" src="/web/image/7"/>
            <p class="edit-me">edit</p>
        </section>
    `);
    await dirtyAndSave(getEditor);
    await Promise.all([measured, saved]);
    expect.verifySteps(["save"]);
    expect(written).toEqual([
        { website_lcp_image_desktop: "/web/image/7", website_lcp_image_mobile: "/web/image/7" },
    ]);
});

test("the url of the elected video is read from its poster", async () => {
    patchObserveLcpEntry((win) => win.document.querySelector("video"));
    const { written, saved } = trackRpcs();
    const { getEditor } = await setupWebsiteBuilder(`
        <section>
            <video poster="/web/static/img/logo2.png" style="width: 800px; height: 400px;"></video>
            <p class="edit-me">edit</p>
        </section>
    `);
    await dirtyAndSave(getEditor);
    await Promise.all([measured, saved]);
    expect.verifySteps(["save"]);
    expect(written).toEqual([
        {
            website_lcp_image_desktop: "/web/static/img/logo2.png",
            website_lcp_image_mobile: "/web/static/img/logo2.png",
        },
    ]);
});

test("an uploaded image field is stored with its rendered url on the first save", async () => {
    const renderedUrl = "/web/image/product.product/12/image_1920/Product?unique=old";
    const uploadedUrl = "/web/static/img/logo2.png";
    patchLcpPlugin({
        electImageUrl(_viewport, snapshot) {
            const imageEl = snapshot.editableCloneEl.querySelector("[data-oe-type='image'] img");
            expect(imageEl).toHaveAttribute("src", uploadedUrl);
            return this.imageUrl(imageEl);
        },
    });
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
    await getEditor().shared.savePlugin.save();
    await Promise.all([measured, saved]);
    expect.verifySteps(["save"]);
    expect(written).toEqual([
        {
            website_lcp_image_desktop: renderedUrl,
            website_lcp_image_mobile: renderedUrl,
        },
    ]);
});

test("the snapshot waits for pending image saves", async () => {
    patchObserveLcpEntry((win) => win.document.querySelector(".target"));
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
    await dirtyAndSave(getEditor);
    await Promise.all([measured, saved]);
    expect.verifySteps(["save"]);
    expect(written).toEqual([
        {
            website_lcp_image_desktop: "/web/image/309-abc123/hero.webp",
            website_lcp_image_mobile: "/web/image/309-abc123/hero.webp",
        },
    ]);
});

test("the measurement frame is painted at the device viewport", async () => {
    const measured = [];
    let notifyMeasured;
    const measuredBothViewports = new Promise((resolve) => (notifyMeasured = resolve));
    patchWithCleanup(LcpMarkingPlugin.prototype, {
        async electImageUrl(...args) {
            return originalElectImageUrl.call(this, ...args);
        },
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
    const { saved } = trackRpcs();
    const { getEditor } = await setupWebsiteBuilder(`
        <section>
            <img class="target" style="width: 800px; height: 400px;" src='${dummyBase64Img}'/>
            <p class="edit-me">edit</p>
        </section>
    `);
    await dirtyAndSave(getEditor);
    await Promise.all([measuredBothViewports, saved]);
    expect.verifySteps(["save"]);
    expect(measured.map((m) => m.viewport).sort()).toEqual(["1199x675", "991x1762"]);
    expect(measured.map((m) => m.clipped)).toEqual([false, false]);
    expect(measured.map((m) => m.outsideViewport)).toEqual([false, false]);
    expect(measured.map((m) => m.reachableBySelectors)).toEqual([false, false]);
});

describe("translation mode", () => {
    async function setupTranslation(content) {
        const written = [];
        const translations = [];
        const archSaves = [];
        onRpc("ir.ui.view", "write", ({ args, kwargs }) => {
            expect(kwargs.context.lang).toBe("fr_BE");
            expect(kwargs.context.website_id).toBe(1);
            written.push(args);
            return true;
        });
        onRpc("ir.ui.view", "save", ({ args }) => {
            archSaves.push(args);
            return true;
        });
        onRpc("/website/field/translation/update", async (request) => {
            translations.push((await request.json()).params);
            return true;
        });
        patchWithCleanup(LcpMarkingPlugin.prototype, {
            async electImageUrl(...args) {
                return originalElectImageUrl.call(this, ...args);
            },
            observeLcpEntry(win) {
                return win.document.querySelector("img");
            },
        });
        await getTranslatedElements();
        const builder = await setupWebsiteBuilder(content, {
            translateMode: true,
            onIframeLoaded(iframe) {
                const doc = iframe.contentDocument;
                doc.documentElement.lang = "fr-BE";
                Object.assign(doc.documentElement.dataset, {
                    websiteId: "1",
                    mainObject: "website.page(4,)",
                    seoObject: "ir.ui.view(1,)",
                    langName: "Français (BE)",
                    defaultLangName: "English (US)",
                    edit_translations: "1",
                });
                getService("website").pageDocument = doc;
            },
        });
        await contains(".modal .btn:contains(Ok, never show me this again)").click();
        return { ...builder, written, translations, archSaves };
    }

    test("translated text saves LCP hints in the active language without saving the view arch", async () => {
        const { getEditor, written, translations, archSaves } = await setupTranslation(`
            <section>
                <img style="width: 800px; height: 400px;" src="/web/image/7"/>
                <p>
                    <span data-oe-model="ir.ui.view" data-oe-id="526" data-oe-field="arch_db"
                        data-oe-translation-state="to_translate"
                        data-oe-translation-source-sha="textSource">Hello</span>
                </p>
            </section>
        `);
        const textNode = getEditor().editable.querySelector("span").firstChild;
        setSelection({
            anchorNode: textNode,
            anchorOffset: 0,
            focusNode: textNode,
            focusOffset: textNode.length,
        });
        await insertText(getEditor(), "Bonjour");
        await saveWebsiteBuilder();
        expect(translations).toEqual([
            {
                model: "ir.ui.view",
                record_id: [526],
                field_name: "arch_db",
                translations: { fr_BE: { textSource: "Bonjour" } },
            },
        ]);
        expect(written).toEqual([
            [
                [1],
                {
                    website_lcp_image_desktop: "/web/image/7",
                    website_lcp_image_mobile: "/web/image/7",
                },
            ],
        ]);
        expect(archSaves).toEqual([]);
    });

    test("translated replacement image hints use the persisted URL after pending image save", async () => {
        const selectedUrl = "/web/static/img/logo2.png";
        const persistedUrl = "/web/image/11-abc123/translated.png";
        let notifyImageSave;
        const imageSaveRequested = new Promise((resolve) => (notifyImageSave = resolve));
        let finishImageSave;
        const imageSaveResponse = new Promise((resolve) => (finishImageSave = resolve));
        onRpc("ir.attachment", "search_read", () => [
            {
                id: 10,
                name: "translated.png",
                mimetype: "image/png",
                image_src: selectedUrl,
                access_token: false,
                public: true,
            },
        ]);
        onRpc("/html_editor/modify_image/10", () => {
            notifyImageSave();
            return imageSaveResponse;
        });
        const { waitSidebarUpdated, written, translations, archSaves } = await setupTranslation(`
            <section>
                <img src="/web/image/website.landscape_md_9" style="width: 800px; height: 400px;"
                    data-oe-translate-src="<span data-oe-model=&quot;ir.ui.view&quot; data-oe-id=&quot;544&quot; data-oe-field=&quot;arch_db&quot; data-oe-translation-state=&quot;to_translate&quot; data-oe-translation-source-sha=&quot;imageSource&quot;>/web/image/website.landscape_md_9</span>"/>
            </section>
        `);
        onRpcImg(selectedUrl);
        onRpc("/html_editor/get_image_info", () => ({
            original: { id: 10, image_src: selectedUrl, mimetype: "image/png" },
        }));
        await contains(":iframe img").click();
        await waitSidebarUpdated();
        await contains("[data-action-id='translateMediaSrc']").click();
        await contains(".modal .o_existing_attachment_cell .o_button_area").click();
        await waitSidebarUpdated();
        const saving = saveWebsiteBuilder();
        await imageSaveRequested;
        expect(written).toEqual([]);
        finishImageSave({ original: persistedUrl });
        await saving;
        expect(translations).toEqual([
            {
                model: "ir.ui.view",
                record_id: [544],
                field_name: "arch_db",
                translations: { fr_BE: { imageSource: persistedUrl } },
            },
        ]);
        expect(written).toEqual([
            [
                [1],
                {
                    website_lcp_image_desktop: persistedUrl,
                    website_lcp_image_mobile: persistedUrl,
                },
            ],
        ]);
        expect(archSaves).toEqual([]);
    });
});
