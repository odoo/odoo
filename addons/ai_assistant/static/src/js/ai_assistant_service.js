/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

/**
 * AI Assistant Service
 * Handles communication with the AI Assistant backend
 */
export const aiAssistantService = {
    dependencies: ["rpc", "notification"],

    start(env, { rpc, notification }) {
        let currentConversation = null;

        return {
            /**
             * Start a new conversation
             */
            async startConversation(contextModule = null, contextModel = null, contextRecordId = null) {
                try {
                    const result = await rpc("/ai_assistant/start_conversation", {
                        context_module: contextModule,
                        context_model: contextModel,
                        context_record_id: contextRecordId,
                    });

                    if (result.success) {
                        currentConversation = result.conversation;
                        return result.conversation;
                    } else {
                        notification.add(result.error || "Failed to start conversation", {
                            type: "danger",
                        });
                        return null;
                    }
                } catch (error) {
                    console.error("Error starting conversation:", error);
                    notification.add("Failed to start conversation", {
                        type: "danger",
                    });
                    return null;
                }
            },

            /**
             * Send a message to the AI
             */
            async sendMessage(conversationId, message, contextModule = null) {
                try {
                    const result = await rpc("/ai_assistant/send_message", {
                        conversation_id: conversationId,
                        message: message,
                        context_module: contextModule,
                    });

                    if (result.success) {
                        currentConversation = result.conversation;
                        return result.message;
                    } else {
                        notification.add(result.error || "Failed to send message", {
                            type: "danger",
                        });
                        return null;
                    }
                } catch (error) {
                    console.error("Error sending message:", error);
                    notification.add("Failed to send message", {
                        type: "danger",
                    });
                    return null;
                }
            },

            /**
             * Get conversation details
             */
            async getConversation(conversationId) {
                try {
                    const result = await rpc("/ai_assistant/get_conversation", {
                        conversation_id: conversationId,
                    });

                    if (result.success) {
                        return result.conversation;
                    } else {
                        notification.add(result.error || "Failed to get conversation", {
                            type: "danger",
                        });
                        return null;
                    }
                } catch (error) {
                    console.error("Error getting conversation:", error);
                    return null;
                }
            },

            /**
             * List conversations
             */
            async listConversations(limit = 10, offset = 0) {
                try {
                    const result = await rpc("/ai_assistant/list_conversations", {
                        limit: limit,
                        offset: offset,
                    });

                    if (result.success) {
                        return {
                            conversations: result.conversations,
                            total: result.total_count,
                        };
                    } else {
                        return { conversations: [], total: 0 };
                    }
                } catch (error) {
                    console.error("Error listing conversations:", error);
                    return { conversations: [], total: 0 };
                }
            },

            /**
             * Close a conversation
             */
            async closeConversation(conversationId) {
                try {
                    const result = await rpc("/ai_assistant/close_conversation", {
                        conversation_id: conversationId,
                    });

                    if (result.success) {
                        if (currentConversation && currentConversation.id === conversationId) {
                            currentConversation = null;
                        }
                        return true;
                    } else {
                        notification.add(result.error || "Failed to close conversation", {
                            type: "danger",
                        });
                        return false;
                    }
                } catch (error) {
                    console.error("Error closing conversation:", error);
                    return false;
                }
            },

            /**
             * Get AI Assistant configuration
             */
            async getConfig() {
                try {
                    const result = await rpc("/ai_assistant/get_config", {});

                    if (result.success) {
                        return result.config;
                    } else {
                        return null;
                    }
                } catch (error) {
                    console.error("Error getting config:", error);
                    return null;
                }
            },

            /**
             * Get current conversation
             */
            getCurrentConversation() {
                return currentConversation;
            },

            /**
             * Set current conversation
             */
            setCurrentConversation(conversation) {
                currentConversation = conversation;
            },
        };
    },
};

registry.category("services").add("ai_assistant", aiAssistantService);
