import { useService } from "@web/core/utils/hooks";
import { useRecordObserver } from "@web/model/relational_model/utils";

import { Component } from "@odoo/owl";

export default class KnowledgeBreadcrumbs extends Component {
    static template = "knowledge.KnowledgeBreadcrumbs";
    static props = {
        record: Object,
    };

    setup() {
        super.setup();
        this.actionService = useService("action");
        this.articlesIndexes = [this.props.record.resId];
        this.articleIndex = 0;
        this.canRestorePreviousAction = this.env.config.breadcrumbs?.length > 1;
        useRecordObserver((record) => {
            // When an article is opened, update the array of ids if it was not opened using the
            // breadcrumbs. For example, if the array of ids is [1,2,3,4] and we are currently on
            // the article 2 after having clicked twice on the back button, opening article 5
            // discards the ids after 2 and appends id 5 to the array ([1,2,5])
            if (record.resId !== this.articlesIndexes[this.articleIndex]) {
                this.articlesIndexes.splice(
                    ++this.articleIndex,
                    this.articlesIndexes.length - this.articleIndex,
                    record.resId,
                );
            }
        });
    }

    get isGoBackEnabled() {
        return this.articleIndex > 0 || this.canRestorePreviousAction;
    }

    get isGoNextEnabled() {
        return this.articleIndex < this.articlesIndexes.length - 1;
    }

    onClickBack() {
        if (this.isGoBackEnabled) {
            if (this.articleIndex === 0) {
                this.actionService.restore();
            } else {
                this.env.openArticle(this.articlesIndexes[--this.articleIndex]);
            }
        }
    }

    onClickNext() {
        if (this.isGoNextEnabled) {
            this.env.openArticle(this.articlesIndexes[++this.articleIndex]);
        }
    }
}
