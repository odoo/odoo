import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";

class SnippetsPowerboxPlugin extends Plugin {
    static id = "alert";
    static dependencies = ["dom", "history"];
    resources = {
        user_commands: [
            {
                id: "s_alert",
                title: _t("Alert"),
                description: _t("Insert an alert snippet"),
                icon: "fa-info",
                run: this.insertSnippet.bind(this, "s_alert"),
                isAvailable: isHtmlContentSupported,
            },
            {
                id: "s_rating",
                title: _t("Rating"),
                description: _t("Insert a rating snippet"),
                icon: "fa-star-half-o",
                run: this.insertSnippet.bind(this, "s_rating"),
                isAvailable: isHtmlContentSupported,
            },
            {
                id: "s_card",
                title: _t("Card"),
                description: _t("Insert a card snippet"),
                icon: "fa-sticky-note",
                run: this.insertSnippet.bind(this, "s_card"),
                isAvailable: isHtmlContentSupported,
            },
            {
                id: "s_share",
                title: _t("Share"),
                description: _t("Insert a share snippet"),
                icon: "fa-share-square-o",
                run: this.insertSnippet.bind(this, "s_share"),
                isAvailable: isHtmlContentSupported,
            },
            {
                id: "s_text_highlight",
                title: _t("Text Highlight"),
                description: _t("Insert a text highlight snippet"),
                icon: "fa-sticky-note",
                run: this.insertSnippet.bind(this, "s_text_highlight"),
                isAvailable: isHtmlContentSupported,
            },
            {
                id: "s_chart",
                title: _t("Chart"),
                description: _t("Insert a chart snippet"),
                icon: "fa-bar-chart",
                run: this.insertSnippet.bind(this, "s_chart"),
                isAvailable: isHtmlContentSupported,
            },
            {
                id: "s_progress_bar",
                title: _t("Progress Bar"),
                description: _t("Insert a progress bar snippet"),
                icon: "fa-spinner",
                run: this.insertSnippet.bind(this, "s_progress_bar"),
                isAvailable: isHtmlContentSupported,
            },
            {
                id: "s_badge",
                title: _t("Badge"),
                description: _t("Insert a badge snippet"),
                icon: "fa-tags",
                run: this.insertSnippet.bind(this, "s_badge"),
                isAvailable: isHtmlContentSupported,
            },
            {
                id: "s_blockquote",
                title: _t("Blockquote"),
                description: _t("Insert a blockquote snippet"),
                icon: "fa-quote-left",
                run: this.insertSnippet.bind(this, "s_blockquote"),
                isAvailable: isHtmlContentSupported,
            },
            {
                id: "s_hr",
                title: _t("Separator"),
                description: _t("Insert a horizontal separator snippet"),
                icon: "fa-minus",
                run: this.insertSnippet.bind(this, "s_hr"),
                isAvailable: isHtmlContentSupported,
            },
        ],
        powerbox_categories: withSequence(110, {
            id: "website",
            name: _t("Website"),
        }),
        powerbox_items: [
            {
                categoryId: "website",
                commandId: "s_alert",
            },
            {
                categoryId: "website",
                commandId: "s_rating",
            },
            {
                categoryId: "website",
                commandId: "s_card",
            },
            {
                categoryId: "website",
                commandId: "s_share",
            },
            {
                categoryId: "website",
                commandId: "s_text_highlight",
            },
            {
                categoryId: "website",
                commandId: "s_chart",
            },
            {
                categoryId: "website",
                commandId: "s_progress_bar",
            },
            {
                categoryId: "website",
                commandId: "s_badge",
            },
            {
                categoryId: "website",
                commandId: "s_blockquote",
            },
            {
                categoryId: "website",
                commandId: "s_hr",
            },
        ],
    };

    insertSnippet(name) {
        const snippet = this.config.snippetModel.getSnippetByName("snippet_content", name);
        const content = snippet.content.cloneNode(true);
        this.dependencies.dom.insert(content);
        this.dependencies.history.addStep();
    }
}

registry.category("website-plugins").add(SnippetsPowerboxPlugin.id, SnippetsPowerboxPlugin);
