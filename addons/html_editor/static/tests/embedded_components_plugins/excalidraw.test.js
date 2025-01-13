import { setupMultiEditor, mergePeersSteps } from "@html_editor/../tests/_helpers/collaboration";
import { describe, expect, test } from "@odoo/hoot";
import {
    animationFrame,
    click,
    drag,
    edit,
    queryAll,
    queryOne,
    queryRect,
    waitFor,
} from "@odoo/hoot-dom";
import { ExcalidrawPlugin } from "@html_editor/others/embedded_components/plugins/excalidraw_plugin/excalidraw_plugin";
import { EmbeddedComponentPlugin } from "@html_editor/others/embedded_component_plugin";
import {
    EmbeddedExcalidrawComponent,
    excalidrawEmbedding,
} from "@html_editor/others/embedded_components/backend/excalidraw/excalidraw";
import { renderToElement } from "@web/core/utils/render";
import {
    defineModels,
    fields,
    models,
    mountView,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { HtmlField } from "@html_editor/fields/html_field";
import { parseHTML } from "@html_editor/utils/html";

describe("HTML Editor Embedded Plugins - Excalidraw", () => {
    patchWithCleanup(EmbeddedExcalidrawComponent, {
        props: ["*"],
    });
    test("The plugin is working in collab", async () => {
        const peerInfos = await setupMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: "<p>[c1}{c1][c2}{c2]a</p>",
            Plugins: [EmbeddedComponentPlugin, ExcalidrawPlugin],
            resources: {
                embeddedComponents: [excalidrawEmbedding],
            },
        });
        const e1 = peerInfos.c1.editor;
        const e2 = peerInfos.c2.editor;

        e1.shared.domInsert(
            parseHTML(
                e1.document,
                `<div data-embedded="draw" data-embedded-props='{"source": "https://excalidraw.com"}'/>`
            )
        );
        e1.dispatch("ADD_STEP");
        await animationFrame();
        expect(e1.editable.querySelectorAll("iframe")).toHaveCount(1);
        expect(e2.editable.querySelectorAll("iframe")).toHaveCount(0);
        mergePeersSteps(peerInfos);
        await animationFrame();
        expect(e2.editable.querySelectorAll("iframe")).toHaveCount(1);
    });
    test("Update source when it's no longer okay", async () => {
        let htmlEditor;
        patchWithCleanup(HtmlField.prototype, {
            onEditorLoad(editor) {
                htmlEditor = editor;
                super.onEditorLoad(editor);
            },
        });
        class Article extends models.Model {
            _name = "knowledge.article";

            body = fields.Html();

            _records = [
                {
                    id: 1,
                    body: `<p class="test_target"/>`,
                },
            ];
        }
        class KnowledgeArticleThread extends models.Model {
            _name = "knowledge.article.thread";
        }
        defineModels([Article, KnowledgeArticleThread]);
        await mountView({
            type: "form",
            resModel: "knowledge.article",
            resId: 1,
            arch: `
                <form>
                    <field widget="html" name="body"/>
                </form>
            `,
        });
        await click(".test_target");
        htmlEditor.shared.domInsert(
            renderToElement(
                "html_editor.EmbeddedExcalidrawBlueprint",
                {
                    embeddedProps: JSON.stringify({ source: "https://impwned.com" }),
                },
                {
                    document: htmlEditor.document,
                }
            )
        );
        htmlEditor.dispatch("ADD_STEP");
        await animationFrame();
        expect(".o_view_nocontent_empty_folder").toHaveCount(1);
        await click(".o_view_nocontent_empty_folder ~ button");
        await animationFrame();
        await click(".modal input.o_input");
        await edit("https://excalidraw.com");
        await click(".modal .btn-primary");
        await animationFrame();
        expect("iframe").toHaveCount(1);
    });
    test("Resizing in collab", async () => {
        const peerInfos = await setupMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: "<p class='test_target'>[c1}{c1][c2}{c2]a</p>",
            Plugins: [EmbeddedComponentPlugin, ExcalidrawPlugin],
            resources: {
                embeddedComponents: [excalidrawEmbedding],
            },
        });
        const e1 = peerInfos.c1.editor;
        const e2 = peerInfos.c2.editor;

        e1.shared.domInsert(
            parseHTML(
                e1.document,
                `<div data-embedded="draw" data-embedded-props='{"source": "https://excalidraw.com"}'/>`
            )
        );
        e1.dispatch("ADD_STEP");
        await animationFrame();
        expect(queryAll("iframe", { root: e1.document })).toHaveCount(1);
        const anchor = e1.document.querySelector("[data-embedded='draw']");
        const iframe = queryOne("iframe", { root: e1.document });
        iframe.style.height = "100%";
        await animationFrame();

        const to = await waitFor(".test_target", { root: e1.document });
        const { moveTo, drop } = await drag(
            queryOne(".o_embedded_draw_handle_right", { root: e1.document }),
            { position: "top-left" }
        );
        await moveTo(to, { root: e1.document });
        await animationFrame();
        await drop();
        await animationFrame();
        const rect = queryRect(".test_target", { root: e1.document });
        const target = queryOne(".test_target", { root: e1.document });
        const expectedHeight =
            rect.top -
            anchor.getBoundingClientRect().top -
            parseInt(window.getComputedStyle(target).marginTop) +
            iframe.ownerDocument.defaultView.frameElement.getBoundingClientRect().top;
        expect(JSON.parse(anchor.dataset.embeddedProps).height).toEqual(`${expectedHeight}px`);
        await animationFrame();
        mergePeersSteps(peerInfos);
        await animationFrame();
        const anchor2 = queryOne("[data-embedded='draw']", { root: e2.document });
        expect(JSON.parse(anchor2.dataset.embeddedProps).height).toEqual(`${expectedHeight}px`);
    });
});
