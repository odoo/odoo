import { Editor } from "@html_editor/editor";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import {
    Component,
    EventBus,
    onWillDestroy,
    onWillStart,
    useExternalListener,
    useState,
    useSubEnv,
} from "@odoo/owl";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { registry } from "@web/core/registry";
import { BuilderOverlayPlugin } from "./plugins/builder_overlay/builder_overlay_plugin";
import { DropZonePlugin } from "./plugins/drop_zone_plugin";
import { ElementToolboxPlugin } from "./plugins/element_toolbox_plugin";
import { HandleDirtyElementPlugin } from "./plugins/handle_dirty_element_plugin";
import { MediaWebsitePlugin } from "./plugins/media_website_plugin";
import { SetupEditorPlugin } from "./plugins/setup_editor_plugin";
import { SnippetModel } from "./snippet_model";
import { BlockTab, blockTab } from "./snippets_menu_tabs/block_tab";
import { CustomizeTab, customizeTab } from "./snippets_menu_tabs/customize_tab";
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";

const BUILDER_PLUGIN = [
    ElementToolboxPlugin,
    BuilderOverlayPlugin,
    DropZonePlugin,
    MediaWebsitePlugin,
    SetupEditorPlugin,
    HandleDirtyElementPlugin,
];

function onIframeLoaded(iframe, callback) {
    const doc = iframe.contentDocument;
    if (doc.readyState === "complete") {
        callback();
    } else {
        iframe.contentWindow.addEventListener("load", callback, { once: true });
    }
}

// todo: Why is it called SnippetsMenu? Should we rename it to BuilderSidebar?
export class SnippetsMenu extends Component {
    static template = "html_builder.SnippetsMenu";
    static components = { BlockTab, CustomizeTab };
    static props = {
        iframe: { type: Object },
        closeEditor: { type: Function },
        snippetsName: { type: String },
    };

    setup() {
        // const actionService = useService("action");
        this.pages = [blockTab, customizeTab];
        this.state = useState({
            canUndo: false,
            canRedo: false,
            activeTab: "blocks",
            selectedToolboxes: undefined,
        });
        useHotkey("control+z", () => this.undo());
        useHotkey("control+y", () => this.redo());
        useHotkey("control+shift+z", () => this.redo());
        this.websiteService = useService("website");
        this.orm = useService("orm");

        useExternalListener(window, "beforeunload", this.onBeforeUnload);

        const editorBus = new EventBus();
        // todo: Why is it the "SnippetsMenu" that is supposed to create the
        // editor? Shouldn't it be the parent component (WebsiteBuilderAction)?
        this.editor = new Editor(
            {
                disableFloatingToolbar: true,
                Plugins: [...MAIN_PLUGINS, ...BUILDER_PLUGIN],
                onChange: () => {
                    this.state.canUndo = this.editor.shared.history.canUndo();
                    this.state.canRedo = this.editor.shared.history.canRedo();
                    editorBus.trigger("STEP_ADDED");
                },
                resources: {
                    change_selected_toolboxes_listeners: (selectedToolboxes) => {
                        this.state.selectedToolboxes = selectedToolboxes;
                        this.setTab("customize");
                    },
                },
                getRecordInfo: (editableEl) => {
                    return {
                        resModel: editableEl.dataset["oeModel"],
                        resId: editableEl.dataset["oeId"],
                        field: editableEl.dataset["oeField"],
                        type: editableEl.dataset["oeType"],
                    };
                },
            },
            this.env.services
        );

        this.snippetModel = useState(
            new SnippetModel(this.env.services, {
                snippetsName: this.props.snippetsName,
            })
        );
        onWillStart(async () => {
            await this.snippetModel.load();
        });

        useSubEnv({
            editor: this.editor,
            editorBus,
        });
        // onMounted(() => {
        //     // actionService.setActionMode("fullscreen");
        // });
        onIframeLoaded(this.props.iframe, () => {
            this.editor.attachTo(this.props.iframe.contentDocument.body.querySelector("#wrapwrap"));
        });
        onWillDestroy(() => {
            this.editor.destroy();
            // actionService.setActionMode("current");
        });
    }

    discard() {
        // TODO: adapt
        this.editor.getContent();
        this.props.closeEditor();
    }

    async save() {
        this.isSaving = true;
        const saveProms = [...this.editor.editable.querySelectorAll(".o_dirty")].map(
            async (dirtyEl) => {
                await this.editor.shared.media.savePendingImages(dirtyEl);
                const cleanedEl = this.editor.shared.dirty.handleDirtyElement(dirtyEl);
                await this.saveView(cleanedEl);
            }
        );
        await Promise.all(saveProms);
        browser.location.reload();
    }

    setTab(tab) {
        this.state.activeTab = tab;
    }

    undo() {
        this.editor.shared.history.undo();
    }

    redo() {
        this.editor.shared.history.redo();
    }

    /**
     * Saves one (dirty) element of the page.
     *
     * @param {HTMLElement} el - the element to save
     */
    async saveView(el) {
        const viewID = Number(el.dataset["oeId"]);
        const result = this.orm.call(
            "ir.ui.view",
            "save",
            [viewID, el.outerHTML, (!el.dataset["oeExpression"] && el.dataset["oeXpath"]) || null],
            {
                context: {
                    website_id: this.websiteService.currentWebsite.id,
                    lang: this.websiteService.currentWebsite.metadata.lang,
                    // TODO: Restore the delay translation feature once it's
                    // fixed, see commit msg for more info.
                    delay_translations: false,
                },
            }
        );
        return result;
    }

    onBeforeUnload(event) {
        if (!this.isSaving && this.editor.shared.dirty.isEditableDirty()) {
            event.returnValue = "Unsaved changes";
        }
    }
}

registry.category("lazy_components").add("website.SnippetsMenu", SnippetsMenu);
