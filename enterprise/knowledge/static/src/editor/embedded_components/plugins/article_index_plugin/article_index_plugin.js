import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";

export class ArticleIndexPlugin extends Plugin {
    static id = "articleIndex";
    static dependencies = ["history", "dom"];
     resources = {
        user_commands: [
            {
                id: "insertArticleIndex",
                title: _t("Index"),
                description: _t("Show nested articles"),
                icon: "fa-list",
                run: this.insertArticleIndex.bind(this),
            },
        ],
        powerbox_categories: [
            withSequence(20, {
                id: "knowledge",
                name: _t("Knowledge"),
            }),
        ],
        powerbox_items: [
            {
                categoryId: "knowledge",
                commandId: "insertArticleIndex",
            }
        ],
    };

    insertArticleIndex() {
        const articleIndexBlueprint = renderToElement("knowledge.ArticleIndexBlueprint");
        this.dependencies.dom.insert(articleIndexBlueprint);
        this.dependencies.history.addStep();
    }
}
