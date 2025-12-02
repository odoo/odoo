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
            defaultLinkAttributes: { rel: "ugc" },
            dropImageAsAttachment: true,
            allowImageTransform: this.props.fullEdit,
            height: this.props.height,
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
