/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from '@web/core/utils/hooks';
import { Dialog } from '@web/core/dialog/dialog';
import { SelectMenu } from '@web/core/select_menu/select_menu';
import { DropdownItem } from '@web/core/dropdown/dropdown_item';
import { user } from "@web/core/user";
import { Component, useEffect, onWillStart, useRef, useState } from '@odoo/owl';

export class ArticleSelectionDialog extends Component {

    static template = 'knowledge.ArticleSelectionDialog';
    static components = { Dialog, DropdownItem, SelectMenu };
    static props = {
        articleSelected: Function,
        close: Function,
        confirmLabel: String,
        title: String,
        parentArticleId: { type: Number, optional: true },
    };


    /**
     * @override
     */
    setup() {
        super.setup();
        this.orm = useService('orm');
        this.placeholderLabel = _t('Choose an Article...');
        this.toggler = useRef('togglerRef');
        this.state = useState({
            selectedArticleName: false,
            knowledgeArticles: [],
            createLabel: ''
        });

        //autofocus
        useEffect((toggler) => {
            toggler.click();
        }, () => [this.toggler.el]);

        onWillStart(async () => {
            await this.fetchArticles();
            this.state.isInternalUser = await user.hasGroup('base.group_user');
        });
    }

    async createKnowledgeArticle(label) {
        const articleId = await this.orm.call(
            'knowledge.article',
            'article_create',
            [],
            {title: label, parent_id: this.props.parentArticleId}
        );
        this.props.articleSelected({articleId: articleId, displayName: `📄 ${label}`});
        this.props.close();
        if (this.props.parentArticleId) {
            this.env.bus.trigger('knowledge.sidebar.insertNewArticle', {
                articleId: articleId,
                name: label,
                icon: '📄',
                parentId: this.props.parentArticleId,
            });
        }
    }

    async fetchArticles(searchValue) {
        this.state.createLabel = _t('Create "%s"', searchValue);
        const domain = [
            ['user_has_access', '=', true],
            ['is_template', '=', false]
        ];
        if (searchValue) {
            domain.push(['name', '=ilike', `%${searchValue}%`]);
        }
        const knowledgeArticles = await this.orm.searchRead(
            'knowledge.article',
            domain,
            ['id', 'display_name', 'root_article_id'], {
                limit: 20
            });
        this.state.knowledgeArticles = knowledgeArticles.map(({ id, display_name, root_article_id }) => {
            return {
                value: {
                    articleId: id,
                    rootArticleName:  root_article_id[0] !== id ? root_article_id[1] : ''
                },
                label: display_name
            };
        });
    }

    async selectArticle(value) {
        this.selectedArticle = this.state.knowledgeArticles.find(knowledgeArticle => knowledgeArticle.value.articleId === value.articleId);
        this.state.selectedArticleName = this.selectedArticle.label;
    }

    confirmArticleSelection() {
        this.props.articleSelected({articleId: this.selectedArticle.value.articleId, displayName: this.selectedArticle.label});
        this.props.close();
    }

}
