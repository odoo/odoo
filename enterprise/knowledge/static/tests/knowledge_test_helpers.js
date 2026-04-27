import { mailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels } from "@web/../tests/web_test_helpers";
import { KnowledgeArticle } from "./mock_server/mock_models/knowledge_article";
import { KnowledgeArticleThread } from "./mock_server/mock_models/knowledge_article_thread";

export function defineKnowledgeModels() {
    return defineModels(knowledgeModels);
}

export const knowledgeModels = { ...mailModels, KnowledgeArticle, KnowledgeArticleThread };
