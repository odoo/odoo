/** @odoo-module **/

import { Dialog } from '@web/core/dialog/dialog';
import { useService } from "@web/core/utils/hooks";
import { SelectMenu } from '@web/core/select_menu/select_menu';

import { Component, onWillStart, useEffect, useRef, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

class MoveArticleDialog extends Component {

    static template = "knowledge.MoveArticleDialog";
    static components = { Dialog, SelectMenu };
    static props = {
        close: Function,
        knowledgeArticleRecord: Object
    };

    setup() {
        this.size = 'md';
        this.title = _t("Move an Article");
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.userService = useService("user");
        this.state = useState({selectedParentArticle: false, selectionDisplayGroups: []});
        this.placeholderLabel = _t('Choose an Article...');
        this.toggler = useRef("togglerRef");

        onWillStart(this.fetchValues);

        //autofocus
        useEffect((toggler) => {
            toggler.click();
        }, () => [this.toggler.el]);

    }

    /**
     * For this dialog we needed to get valid articles and the sections since the user can move an
     * article either under a specific article, that becomes its parent, or inside a section, to become a
     * root article in either the workspace or the private section.
     *
     * @param {String} searchValue Term inputted by the user in the SelectMenu's input
     */
    async fetchValues(searchValue) {
        const knowledgeArticles = await this.orm.call(
            'knowledge.article',
            'get_valid_parent_options',
            [this.props.knowledgeArticleRecord.resId],
            {search_term: searchValue}
        );
        const formattedKnowledgeArticles = knowledgeArticles.map(({id, display_name, root_article_id}) => {
            return {
                value: {
                    parentArticleId: id,
                    rootArticleName:  root_article_id[0] !== id ? root_article_id[1] : ''
                },
                label: display_name
            };
        });
        const selectionGroups = [
            {
                label: _t('Categories'),
                choices: [
                    {
                        value: {parentArticleId: 'private'},
                        label: _t('Private'),
                    },
                    {
                        value: {parentArticleId: 'workspace'},
                        label: _t('Workspace')
                    }
                ],
            },
            {
                label: _t('Articles'),
                choices: formattedKnowledgeArticles,
            }
        ];
        this.state.selectionDisplayGroups = selectionGroups;
        this.state.choices = [
            ...selectionGroups[0].choices,
            ...formattedKnowledgeArticles
        ];
    }

    selectArticle(value) {
        this.state.selectedParentArticle = this.state.choices.find(
            (knowledgeArticle) => knowledgeArticle.value.parentArticleId === value.parentArticleId
        );
    }

    async confirmArticleMove() {
        if (!this.state.selectedParentArticle){
            // return if no data selectedParentArticle in the SelectMenu
            return;
        }
        const selectedParentArticle = this.state.selectedParentArticle.value.parentArticleId;
        const params = {};
        if (typeof selectedParentArticle === 'number') {
            params.parent_id = selectedParentArticle;
        } else {
            params.category = selectedParentArticle;
        }
        await this.orm.call(
            'knowledge.article',
            'move_to',
            [this.props.knowledgeArticleRecord.resId],
            params
        );
        // Reload the current article to apply changes
        await this.props.knowledgeArticleRecord.model.load();
        this.props.close();
    }

    get loggedUserPicture() {
        return `/web/image?model=res.users&field=avatar_128&id=${this.userService.userId}`;
    }

    get moveArticleLabel() {
        return _t('Move "%s" under:', this.props.knowledgeArticleRecord.data.display_name);
    }
}

export default MoveArticleDialog;
