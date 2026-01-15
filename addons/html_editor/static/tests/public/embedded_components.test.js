import { before, describe, expect, test } from "@odoo/hoot";
import { animationFrame, queryOne } from "@odoo/hoot-dom";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";
import {
    EmbeddedComponentInteraction,
    getEmbeddingMap,
} from "@html_editor/public/embedded_components/embedded_component_interaction";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { EmbeddedWrapperMixin, embedding } from "@html_editor/../tests/_helpers/embedded_component";
import { getEditableDescendants } from "@html_editor/others/embedded_component_utils";

setupInteractionWhiteList("html_editor.embedded_component");

describe.current.tags("interaction_dev");

function setupEmbeddedComponentsWhitelist(embeddings) {
    before(() => {
        patchWithCleanup(EmbeddedComponentInteraction.prototype, {
            getEmbedding(name) {
                return getEmbeddingMap(embeddings).get(name);
            },
        });
    });
}

describe("Mount and Destroy embedded components", () => {
    test("Can mount and destroy embedded components in editable descendants", async () => {
        const SimpleEmbeddedWrapper = EmbeddedWrapperMixin("deep");
        setupEmbeddedComponentsWhitelist([
            embedding("wrapper", SimpleEmbeddedWrapper, (host) => ({ host }), {
                getEditableDescendants,
            }),
        ]);
        const { core } = await startInteractions(
            `<div data-embedded="wrapper">
                <div data-embedded-editable="deep">
                    <div data-embedded="wrapper">
                        <div data-embedded-editable="deep">
                            <p>deep</p>
                        </div>
                    </div>
                </div>
            </div>`
        );
        await animationFrame();
        expect(queryOne("#wrapwrap")).toHaveInnerHTML(
            `<div data-embedded="wrapper">
                <owl-root contenteditable="false" data-oe-protected="true" style="display: contents;">
                    <div class="deep">
                        <div data-embedded-editable="deep">
                            <div data-embedded="wrapper">
                                <owl-root contenteditable="false" data-oe-protected="true" style="display: contents;">
                                    <div class="deep">
                                        <div data-embedded-editable="deep">
                                            <p>deep</p>
                                        </div>
                                    </div>
                                </owl-root>
                            </div>
                        </div>
                    </div>
                </owl-root>
            </div>`
        );
        core.stopInteractions();
        expect(queryOne("#wrapwrap")).toHaveInnerHTML(
            `<div data-embedded="wrapper">
                <div data-embedded-editable="deep">
                    <div data-embedded="wrapper">
                        <div data-embedded-editable="deep">
                            <p>deep</p>
                        </div>
                    </div>
                </div>
            </div>`
        );
    });
    test("Keep existing HTML content and do not crash when encountering an unknown data-embedded value", async () => {
        await startInteractions(
            `<div data-embedded="wrapper">
                <div data-embedded-editable="deep">
                    <div data-embedded="wrapper">
                        <div data-embedded-editable="deep">
                            <p>deep</p>
                        </div>
                    </div>
                </div>
            </div>`
        );
        await animationFrame();
        expect(queryOne("#wrapwrap")).toHaveInnerHTML(
            `<div data-embedded="wrapper">
                <div data-embedded-editable="deep">
                    <div data-embedded="wrapper">
                        <div data-embedded-editable="deep">
                            <p>deep</p>
                        </div>
                        <owl-root contenteditable="false" data-oe-protected="true" style="display: contents;"></owl-root>
                    </div>
                </div>
                <owl-root contenteditable="false" data-oe-protected="true" style="display: contents;"></owl-root>
            </div>`
        );
    });
});
