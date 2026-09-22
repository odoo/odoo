import { AddSnippetDialog } from "@html_builder/snippets/add_snippet_dialog";
import { isBrowserSafari } from "@web/core/browser/feature_detection";
import { renderToFragment } from "@web/core/utils/render";

export class AddSnippetDialogSandboxed extends AddSnippetDialog {
    static template = "mass_mailing.AddSnippetDialog";

    get isBrowserSafari() {
        return isBrowserSafari();
    }

    getDefaultAssets() {
        return ["mass_mailing.iframe_add_dialog"];
    }

    renderIframeHead() {
        const iframe = this.iframeRef();
        iframe.contentDocument.head.prepend(renderToFragment("mass_mailing.IframeHead"));
    }
}
