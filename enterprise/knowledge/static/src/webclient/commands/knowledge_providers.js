/** @odoo-module */


import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { HotkeyCommandItem } from "@web/core/commands/default_providers";
import { DefaultCommandItem, splitCommandName } from "@web/core/commands/command_palette";
import { markup } from "@odoo/owl";
import { user } from "@web/core/user";

// Articles command
class KnowledgeCommand extends DefaultCommandItem {
    static template = "KnowledgeCommandTemplate";
    static props = {
        ...DefaultCommandItem.props,
        headline: String,
        icon_string: String,
        isFavorite: Boolean,
        splitSubjectName: Array,
        subjectName: [String, Boolean],
    };
}

// "Not found, create one" command
class Knowledge404Command extends DefaultCommandItem {
    static template = "Knowledge404CommandTemplate";
    static props = {
        ...DefaultCommandItem.props,
        articleName: String,
    };
}

// Advanced search command
class KnowledgeExtraCommand extends HotkeyCommandItem {
    static template = "KnowledgeExtraCommandTemplate";
}

const commandSetupRegistry = registry.category("command_setup");
commandSetupRegistry.add("?", {
    debounceDelay: 500,
    emptyMessage: _t("No article found."),
    name: _t("articles"),
    placeholder: _t("Search for an article..."),
});

const commandProviderRegistry = registry.category("command_provider");

const fn = (hidden) => {
    // Check if the user has enough rights to create a new article
    const canCreate = () => user.checkAccessRight("knowledge.article", "create");
    let articlesData;
    return async function provide(env, options) {
        articlesData = await env.services.orm.call(
            "knowledge.article",
            "get_user_sorted_articles",
            [[]],
            {
                search_query: options.searchValue,
                hidden_mode: hidden,
            }
        );
        if (!hidden){
            if (articlesData.length === 0) {
                // Only display the "create article" command when the user can
                // create an article and when the user inputs at least 3 characters
                if (options.searchValue.length > 2 && await canCreate()) {
                    return [{
                        Component: Knowledge404Command,
                        async action() {
                            const articleId = await env.services.orm.call(
                                'knowledge.article',
                                'article_create',
                                [options.searchValue],
                                {
                                    is_private: true
                                },
                            );

                            env.services.action.doAction('knowledge.ir_actions_server_knowledge_home_page', {
                                additionalContext: {
                                    res_id: articleId,
                                }
                            });
                        },
                        name: _t('No Article found. Create "%s"', options.searchValue),
                        props: {
                            articleName: options.searchValue,
                        },
                    }];
                }
                else {
                    return [];
                }
            }
        }
        const knowledgeMainMenuId = env.services.menu.getAll().find(
            menu => menu.xmlid === 'knowledge.knowledge_menu_root'
        ).id;
        // display the articles
        const result = articlesData.map(article => ({
            Component: KnowledgeCommand,
            action() {
                env.services.action.doAction('knowledge.ir_actions_server_knowledge_home_page', {
                    additionalContext: {
                        res_id: article.id,
                    }
                });

            },
            category: "knowledge_articles",
            href: `/odoo/knowledge.article/${article.id}?menu_id=${knowledgeMainMenuId}`,
            name: article.name || _t("Untitled"),
            props: {
                isFavorite: article.is_user_favorite,
                headline: article.headline ? markup(article.headline) : '',
                subjectName: article.root_article_id[0] != article.id ? article.root_article_id[1] : false,
                splitSubjectName: splitCommandName(article.root_article_id[1], options.searchValue),
                icon_string: article.icon || '📄',
            },
        }));
        if(!hidden){
        // add the "advanced search" command
            result.push({
                Component: KnowledgeExtraCommand,
                async action() {
                    const articleIds = articlesData.map(article => article.id);
                    const action = await env.services.action.loadAction('knowledge.knowledge_article_action');
                    delete action.context.search_default_filter_not_is_article_item;
                    env.services.action.doAction(action, {
                        additionalContext: {
                            search_default_filter_search_article_ids: 1,
                            search_article_ids: articleIds,
                        },
                    });
                },
                category: "knowledge_extra",
                name: _t("Advanced Search"),
                props: {
                    hotkey: "alt+B",
                },
            });
        }
        return result;
    };
};

commandProviderRegistry.add("knowledge", {
    debounceDelay: 500,
    namespace: "?",
    provide: fn(false),
});

commandSetupRegistry.add("$", {
    debounceDelay: 500,
    emptyMessage: _t("Oops, there's nothing here. Try another search."),
    placeholder: _t("Search hidden Articles..."),
});
commandProviderRegistry.add("knowledge_members_only_articles", {
    debounceDelay: 500,
    namespace: "$",
    provide: fn(true),
});
