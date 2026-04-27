import { Plugin } from "@html_editor/plugin";
import { boundariesOut } from "@html_editor/utils/position";
import { EMBEDDED_COMPONENT_PLUGINS } from "@html_editor/plugin_sets";
import { _t } from "@web/core/l10n/translation";

export class EmbeddedViewLinkPlugin extends Plugin {
    static id = "embeddedViewLink";
    static dependencies = ["history", "dom", "selection"];
    resources = {
        mount_component_handlers: this.setupNewComponent.bind(this),
    };

    setupNewComponent({ name, props }) {
        if (name === "viewLink") {
            Object.assign(props, {
                removeViewLink: (text) => {
                    this.replaceElementWith(props.host, text);
                    this.dependencies.history.addStep();
                },
                copyViewLink: () => {
                    const cursors = this.dependencies.selection.preserveSelection();
                    this.copyElementToClipboard(props.host);
                    cursors?.restore();
                },
            });
        }
    }

    replaceElementWith(target, element) {
        const [anchorNode, anchorOffset, focusNode, focusOffset] = boundariesOut(target);
        this.dependencies.selection.setSelection({
            anchorNode,
            anchorOffset,
            focusNode,
            focusOffset,
        });
        this.dependencies.dom.insert(element);
    }

    copyElementToClipboard(element) {
        const range = document.createRange();
        range.selectNode(element);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        const copySucceeded = document.execCommand("copy");
        selection.removeAllRanges();
        if (copySucceeded) {
            this.services.notification.add(_t("Link copied to clipboard."), {
                type: "success",
            });
        }
    }
}

EMBEDDED_COMPONENT_PLUGINS.push(EmbeddedViewLinkPlugin);
