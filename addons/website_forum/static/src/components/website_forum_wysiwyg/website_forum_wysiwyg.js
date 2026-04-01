import { removeClass } from "@html_editor/utils/dom";
import { markup, onMounted, useExternalListener } from "@odoo/owl";
import { BASIC_PLUGINS, FULL_EDIT_PLUGINS } from "../../plugins/plugin_sets";
import { useResizer } from "./resizer_hook";
import { Wysiwyg } from "@html_editor/wysiwyg";

export class WebsiteForumWysiwyg extends Wysiwyg {
    static template = "website_forum.WebsiteForumWysiwyg";
    static props = {
        ...super.props,
        textareaEl: HTMLElement,
        fullEdit: Boolean,
        getRecordInfo: Function,
        resizable: { type: Boolean, optional: true },
        height: { type: String, optional: true },
    };
    static defaultProps = {
        ...super.defaultProps,
        class: "odoo-editor",
        contentClass: "note-editable",
    };

    /** @override */
    setup() {
        super.setup();
        if (this.props.resizable) {
            // Event listener added on template.
            this.onResizerMouseDown = useResizer("content");
        }
        const form = this.props.textareaEl.closest("form");
        // Prevent form submission behavior of buttons inside the form
        onMounted(() =>
            form.querySelectorAll(".o-wysiwyg button").forEach((btn) => (btn.type = "button"))
        );
        this.submitButton = form.querySelector("button[type=submit]");
        useExternalListener(this.submitButton, "click", this.onSubmitButtonClick.bind(this));
        this.readyToSubmit = false;

        const postReplyWrapper = form.closest("#post_reply");
        if (postReplyWrapper) {
            const clearSelection = () =>
                this.editor.shared.selection.setCursorStart(this.editor.editable);

            // On post reply, the discard button simply hides the editable.
            // Clear the selection to close any overlay dependent on an uncollapsed
            // selection (like the toolbar).
            const discardButton = postReplyWrapper.querySelector(".o_wforum_discard_btn");
            useExternalListener(discardButton, "click", clearSelection);

            // Expanding to full view changes the editable's position.
            // Clear the selection to close overlays.
            const toggleExpandButton = postReplyWrapper.querySelector(".o_wforum_expand_toggle");
            useExternalListener(toggleExpandButton, "click", clearSelection);
        }
    }

    /** @override */
    getEditorConfig() {
        return {
            getRecordInfo: this.props.getRecordInfo,
            Plugins: this.props.fullEdit ? FULL_EDIT_PLUGINS : BASIC_PLUGINS,
            content: this.getTextAreaContent(),
            resources: {
                start_edition_handlers: () => this.cleanImageClasses(this.editor.editable),
                clean_for_save_handlers: ({ root }) => this.cleanImageClasses(root),
            },
            defaultLinkAttributes: { rel: "ugc noreferrer noopener", target: "_blank" },
            dropImageAsAttachment: true,
            allowImageTransform: false,
            height: this.props.height,
            allowImageResize: false,
            allowFontFamily: false,
        };
    }

    cleanImageClasses(root) {
        // float-start class messes up the post layout OPW 769721
        const classNames = ["o_we_selected_image", "float-start"];
        root.querySelectorAll("img").forEach((img) => removeClass(img, ...classNames));
    }

    getTextAreaContent() {
        const textarea = this.props.textareaEl;
        let content = textarea.getAttribute("content") || textarea.value || "";
        content = DOMPurify.sanitize(content, { ADD_ATTR: ["contenteditable"] });
        if (!content.trim()) {
            content = "<p><br></p>";
        }
        return markup(content);
    }

    onSubmitButtonClick(ev) {
        if (this.readyToSubmit) {
            this.readyToSubmit = false;
            return;
        }
        ev.preventDefault();
        this.editor.shared.imageSave.savePendingImages().finally(() => {
            this.props.textareaEl.value = this.editor.getContent();
            this.readyToSubmit = true;
            this.submitButton.click();
        });
    }
}
