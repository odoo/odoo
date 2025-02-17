import { Builder } from "@html_builder/builder";
import { DropZonePlugin } from "@html_builder/core/plugins/drop_zone_plugin";
import { LocalOverlayContainer } from "@html_editor/local_overlay_container";
import { animationFrame } from "@odoo/hoot-dom";
import { Component, onMounted, useRef, useState, useSubEnv, xml } from "@odoo/owl";
import {
    mountWithCleanup,
    patchWithCleanup,
    defineModels,
    models,
} from "@web/../tests/web_test_helpers";
import { getWebsiteSnippets } from "./snippets_getter.hoot";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";

function getSnippetView(snippets) {
    const { snippet_groups, snippet_custom, snippet_structure, snippet_content } = snippets;
    return `
    <snippets id="snippet_groups" string="Categories">
        ${(snippet_groups || []).join("")}
    </snippets>
    <snippets id="snippet_structure" string="Structure">
        ${(snippet_structure || []).join("")}
    </snippets>
    <snippets id="snippet_custom" string="Custom">
        ${(snippet_custom || []).join("")}
    </snippets>
    <snippets id="snippet_content" string="Inner Content">
        ${(snippet_content || []).join("")}
    </snippets>`;
}

function getSnippetStructure({ name, content, keywords = [], groupName, imagePreview = "" }) {
    keywords = keywords.join(", ");
    return `<div name="${name}" data-oe-snippet-id="123" data-o-image-preview="${imagePreview}" data-oe-keywords="${keywords}" data-o-group="${groupName}">${content}</div>`;
}

class IrUiView extends models.Model {
    _name = "ir.ui.view";
    render_public_asset() {
        return getWebsiteSnippets();
    }
}

class BuilderContainer extends Component {
    static template = xml`
        <div class="d-flex h-100 w-100" t-ref="container">
            <div class="o_website_preview flex-grow-1" t-ref="website_preview">
                <div class="o_iframe_container">
                    <iframe class="h-100 w-100" t-ref="iframe" />
                    <div t-if="this.state.isMobile" class="o_mobile_preview_layout">
                        <img alt="phone" src="/html_builder/static/img/phone.png"/>
                    </div>
                </div>
            </div>
            <LocalOverlayContainer localOverlay="overlayRef" identifier="env.localOverlayContainerKey"/>
            <div t-if="state.isEditing" t-att-class="{'o_builder_sidebar_open': state.isEditing}" class="o-website-builder_sidebar border-start border-dark">
                <Builder t-props="this.getBuilderProps()"/>
            </div>
        </div>`;
    static components = { Builder, LocalOverlayContainer };
    static props = { content: String };

    setup() {
        this.state = useState({ isMobile: false, isEditing: false });
        this.iframeRef = useRef("iframe");
        this.iframeLoaded = new Promise((resolve) => {
            onMounted(() => {
                const el = this.iframeRef.el;
                el.contentDocument.body.innerHTML = `<div id="wrapwrap"><div id="wrap" class="oe_structure oe_empty" data-oe-model="ir.ui.view" data-oe-id="539" data-oe-field="arch">${this.props.content}</div></div>`;
                resolve(el);
            });
        });
        useSubEnv({
            builderRef: useRef("container"),
        });
    }

    getBuilderProps() {
        return {
            closeEditor: () => {},
            snippetsName: "",
            toggleMobile: () => {
                this.state.isMobile = !this.state.isMobile;
            },
            overlayRef: () => {},
            isTranslation: false,
            iframeLoaded: this.iframeLoaded,
            isMobile: this.state.isMobile,
        };
    }
}

export async function setupHTMLBuilder(content = "") {
    let snippetContent = null;

    defineMailModels(); // fuck this shit
    defineModels([IrUiView]);

    const getSnippetEl = (withColoredLevelClass = false) => {
        const className = withColoredLevelClass ? "s_test o_colored_level" : "s_test";
        return `<section class="${className}" data-snippet="s_test" data-name="Test">
            <div class="test_a"></div>
        </section>`;
    };
    const snippetsDescription = () => [{ name: "Test", groupName: "a", content: getSnippetEl() }];
    const snippetsDescr = {
        snippet_groups: [
            '<div name="A" data-oe-thumbnail="a.svg" data-oe-snippet-id="123" data-o-snippet-group="a"><section data-snippet="s_snippet_group"></section></div>',
        ],
        snippet_structure: snippetsDescription().map((snippetDesc) =>
            getSnippetStructure(snippetDesc)
        ),
    };
    patchWithCleanup(IrUiView.prototype, {
        render_public_asset: () => getSnippetView(snippetsDescr),
    });
    let _resolve;
    const prom = new Promise((resolve) => {
        _resolve = resolve;
    });

    // hack to get a promise that resolves when editor is ready
    patchWithCleanup(DropZonePlugin.prototype, {
        setup() {
            super.setup();
            _resolve();
        },
    });
    const comp = await mountWithCleanup(BuilderContainer, { props: { content } });
    await comp.iframeLoaded;
    comp.state.isEditing = true;
    await animationFrame();
    await animationFrame();
    await prom;
    await animationFrame();
    return {
        contentEl: comp.iframeRef.el.contentDocument.body.firstChild.firstChild,
        snippetContent: getSnippetEl(true),
    };
}
