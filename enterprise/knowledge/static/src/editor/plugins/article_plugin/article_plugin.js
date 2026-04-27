import { Plugin } from "@html_editor/plugin";
import { rightPos } from "@html_editor/utils/position";
import { ArticleSelectionDialog } from "@knowledge/components/article_selection_dialog/article_selection_dialog";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";

const ARTICLE_LINKS_SELECTOR = ".o_knowledge_article_link";
export class KnowledgeArticlePlugin extends Plugin {
    static id = "article";
    static dependencies = ["history", "dom", "selection", "dialog"];
    resources = {
        user_commands: [
            {
                id: "insertArticle",
                title: _t("Article"),
                description: _t("Insert an Article shortcut"),
                icon: "fa-newspaper-o",
                run: this.addArticle.bind(this),
            },
        ],
        powerbox_items: [
            {
                categoryId: "navigation",
                commandId: "insertArticle",
            },
        ],
        clean_for_save_handlers: this.cleanForSave.bind(this),
        normalize_handlers: this.normalize.bind(this),
    };

    setup() {
        super.setup();
        this.boundOpenArticle = this.openArticle.bind(this);
    }

    addArticle() {
        const recordInfo = this.config.getRecordInfo();
        let parentArticleId;
        if (recordInfo.resModel === "knowledge.article" && recordInfo.resId) {
            parentArticleId = recordInfo.resId;
        }
        this.dependencies.dialog.addDialog(ArticleSelectionDialog, {
            title: _t("Link an Article"),
            confirmLabel: _t("Insert Link"),
            articleSelected: (article) => {
                const articleLinkBlock = renderToElement("knowledge.ArticleBlueprint", {
                    href: `/knowledge/article/${article.articleId}`,
                    articleId: article.articleId,
                    displayName: article.displayName,
                });

                this.dependencies.dom.insert(articleLinkBlock);
                this.dependencies.history.addStep();
                const [anchorNode, anchorOffset] = rightPos(articleLinkBlock);
                this.dependencies.selection.setSelection({ anchorNode, anchorOffset });
            },
            parentArticleId,
        });
    }

    scanForArticleLinks(element) {
        const articleLinks = [...element.querySelectorAll(ARTICLE_LINKS_SELECTOR)];
        if (element.matches(ARTICLE_LINKS_SELECTOR)) {
            articleLinks.unshift(element);
        }
        return articleLinks;
    }

    async openArticle(ev) {
        if (this.config.embeddedComponentInfo?.env?.openArticle) {
            const articleId = parseInt(ev.target.dataset.res_id);
            if (articleId) {
                ev.preventDefault();
                await this.config.embeddedComponentInfo.env.openArticle(articleId);
            }
        }
    }

    normalize(element) {
        const articleLinks = this.scanForArticleLinks(element);
        for (const articleLink of articleLinks) {
            articleLink.setAttribute("target", "_blank");
            articleLink.setAttribute("contenteditable", "false");
            articleLink.addEventListener("click", this.boundOpenArticle);
        }
    }

    cleanForSave({ root }) {
        const articleLinks = this.scanForArticleLinks(root);
        for (const articleLink of articleLinks) {
            articleLink.removeAttribute("contenteditable");
        }
    }

    destroy() {
        super.destroy();
        const articleLinks = this.scanForArticleLinks(this.editable);
        for (const articleLink of articleLinks) {
            articleLink.removeEventListener("click", this.boundOpenArticle);
        }
    }
}
