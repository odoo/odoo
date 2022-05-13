/** @odoo-module */


import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { HotkeyCommandItem } from "@web/core/commands/default_providers";
import { splitCommandName } from "@web/core/commands/command_palette";

const { Component } = owl;

// Articles command
class KnowledgeCommand extends Component {}
KnowledgeCommand.template = 'KnowledgeCommandTemplate';

// "Not found, create one" command
class Knowledge404Command extends Component {}
Knowledge404Command.template = 'Knowledge404CommandTemplate';

// Advanced search command
class KnowledgeExtraCommand extends HotkeyCommandItem {}
KnowledgeExtraCommand.template = 'KnowledgeExtraCommandTemplate';

const commandSetupRegistry = registry.category("command_setup");
commandSetupRegistry.add("?", {
    debounceDelay: 200,
    emptyMessage: _lt("No article found."),
    name: _lt("articles"),
});

const commandProviderRegistry = registry.category("command_provider");
commandProviderRegistry.add("knowledge", {
    debounceDelay: 200,
    namespace: "?",
    async provide(env, options) {
        const articlesData = await Component.env.services.rpc({
            model: "knowledge.article",
            method: "get_user_sorted_articles",
            args: [[]],
            kwargs: {
                search_query: options.searchValue,
            }
        });

        if (articlesData.length === 0) {
            // check if user has enough rights to create a new article
            const canCreate = await Component.env.services.rpc({
                model: "knowledge.article",
                method: "check_access_rights",
                kwargs: {
                    operation: "create",
                    raise_exception: false,
                },
            });
            // only display the "create article" command when there are at least 3 character
            if (canCreate && options.searchValue.length > 2) {
                return [{
                    Component: Knowledge404Command,
                    async action() {
                        const articleId = await Component.env.services.rpc({
                            model: 'knowledge.article',
                            method: 'article_create',
                            args: [[options.searchValue]],
                            kwargs: {
                                is_private: true
                            },
                        });

                        env.services.action.doAction('knowledge.ir_actions_server_knowledge_home_page', {
                            additionalContext: {
                                res_id: articleId,
                            }
                        });
                    },
                    name: "No Article found. Create \"" + options.searchValue + "\"",
                    props: {
                        articleName: options.searchValue,
                    },
                }];
            }
            else {
                return [];
            }
        }
        // display the articles
        let result =  articlesData.map((article) => ({
            Component: KnowledgeCommand,
            action() {
                env.services.action.doAction('knowledge.ir_actions_server_knowledge_home_page', {
                    additionalContext: {
                        res_id: article.id,
                    }
                });

            },
            category: "knowledge_articles",
            name: article.name,
            props: {
                isFavorite: article.is_user_favorite,
                subjectName: article.root_article_id[0] != article.id ? article.root_article_id[1] : false,
                splitSubjectName: splitCommandName(article.root_article_id[1], options.searchValue),
                icon_string: article.icon,
            },
        }));
        // add the "advanced search" command
        result.push({
            Component: KnowledgeExtraCommand,
            action() {
                env.services.action.doAction({
                    type: "ir.actions.act_window",
                    res_model: "knowledge.article",
                    search_view_id: [false, "search"],
                    views: [[false, "list"]],
                    target: "current",
                    context: {
                        search_default_name: options.searchValue,
                    },
                    name: "Search Articles",
                })
            },
            category: "knowledge_extra",
            name: "Advanced Search",
            props: {
                hotkey: "alt+B",
            },
        });
        return result;
    },
});
