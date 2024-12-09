import { setupMultiEditor, mergePeersSteps } from "@html_editor/../tests/_helpers/collaboration";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { EmbeddedComponentPlugin } from "@html_editor/others/embedded_component_plugin";
import { TableOfContentPlugin } from "@html_editor/others/embedded_components/plugins/table_of_content_plugin/table_of_content_plugin";
import { tableOfContentEmbedding } from "@html_editor/others/embedded_components/core/table_of_content/table_of_content";
import { parseHTML } from "@html_editor/utils/html";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

describe("HTML Editor Embedded Plugins - Table of Content", () => {
    beforeEach(() => {
        patchWithCleanup(TableOfContentPlugin.prototype, {
            delayedUpdateTableOfContents(element) {
                super.delayedUpdateTableOfContents(element);
                window.clearTimeout(this.updateTimeout);
                this.manager.updateStructure();
            },
        });
    });
    test("The plugin is working in collab", async () => {
        const peerInfos = await setupMultiEditor({
            peerIds: ["c1", "c2"],
            contentBefore: "<p>[c1}{c1][c2}{c2]a</p>",
            Plugins: [EmbeddedComponentPlugin, TableOfContentPlugin],
            resources: {
                embeddedComponents: [tableOfContentEmbedding],
            },
        });
        const e1 = peerInfos.c1.editor;
        const e2 = peerInfos.c2.editor;

        e1.shared.domInsert(
            parseHTML(
                e1.document,
                `<div data-embedded="tableOfContent" data-oe-protected="true" contenteditable="false"/>`
            )
        );
        e1.dispatch("ADD_STEP");
        await animationFrame();
        expect(e1.document.querySelectorAll("[data-embedded='tableOfContent']")).toHaveCount(1);
        expect(e2.document.querySelectorAll("[data-embedded='tableOfContent']")).toHaveCount(0);
        mergePeersSteps(peerInfos);
        expect(e2.document.querySelectorAll("[data-embedded='tableOfContent']")).toHaveCount(1);
        e1.shared.domInsert(
            parseHTML(
                e1.document,
                `<h1>Head 1</h1>
                <h2>Head 1.1</h2>
                <h3>Head 1.1.1</h3>
                <h2>Head 1.2</h2>
                <h1>Head 2</h1>
                `
            )
        );
        e1.dispatch("ADD_STEP");
        await animationFrame();
        expect(e1.editable.querySelectorAll(".o_embedded_toc_link")).toHaveCount(5);
        expect(e2.editable.querySelectorAll(".o_embedded_toc_link")).toHaveCount(0);
        mergePeersSteps(peerInfos);
        await animationFrame();
        expect(e2.editable.querySelectorAll(".o_embedded_toc_link")).toHaveCount(5);
    });
});
