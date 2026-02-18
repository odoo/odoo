/** @odoo-module **/

import { Component, useState, useRef, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * AI Chat Window Component
 */
export class AIChatWindow extends Component {
    setup() {
        this.aiAssistant = useService("ai_assistant");
        this.action = useService("action");

        this.state = useState({
            isOpen: false,
            isMinimized: false,
            conversation: null,
            messages: [],
            inputMessage: "",
            isLoading: false,
            error: null,
        });

        this.messagesEndRef = useRef("messagesEnd");
        this.inputRef = useRef("messageInput");
    }

    /**
     * Toggle chat window
     */
    async toggleChat() {
        if (!this.state.isOpen) {
            await this.openChat();
        } else {
            this.closeChat();
        }
    }

    /**
     * Open chat window
     */
    async openChat() {
        this.state.isOpen = true;
        this.state.isMinimized = false;

        // Check if we have a current conversation
        const currentConv = this.aiAssistant.getCurrentConversation();

        if (currentConv) {
            this.state.conversation = currentConv;
            this.state.messages = currentConv.messages || [];
        } else {
            // Start new conversation
            await this.startNewConversation();
        }

        // Focus input
        setTimeout(() => {
            if (this.inputRef.el) {
                this.inputRef.el.focus();
            }
        }, 100);
    }

    /**
     * Close chat window
     */
    closeChat() {
        this.state.isOpen = false;
    }

    /**
     * Minimize/maximize chat
     */
    toggleMinimize() {
        this.state.isMinimized = !this.state.isMinimized;
    }

    /**
     * Start a new conversation
     */
    async startNewConversation() {
        this.state.isLoading = true;
        this.state.error = null;

        try {
            // Get current context from action manager if available
            const context = this.getCurrentContext();

            const conversation = await this.aiAssistant.startConversation(
                context.module,
                context.model,
                context.recordId
            );

            if (conversation) {
                this.state.conversation = conversation;
                this.state.messages = conversation.messages || [];
                this.scrollToBottom();
            } else {
                this.state.error = "Failed to start conversation";
            }
        } catch (error) {
            console.error("Error starting conversation:", error);
            this.state.error = "An error occurred";
        } finally {
            this.state.isLoading = false;
        }
    }

    /**
     * Send a message
     */
    async sendMessage() {
        const message = this.state.inputMessage.trim();

        if (!message || this.state.isLoading) {
            return;
        }

        if (!this.state.conversation) {
            await this.startNewConversation();
            if (!this.state.conversation) {
                return;
            }
        }

        // Add user message to UI immediately
        const userMessage = {
            role: "user",
            content: message,
            create_date: new Date().toISOString(),
        };
        this.state.messages.push(userMessage);
        this.state.inputMessage = "";
        this.scrollToBottom();

        // Send to backend
        this.state.isLoading = true;
        this.state.error = null;

        try {
            const context = this.getCurrentContext();
            const assistantMessage = await this.aiAssistant.sendMessage(
                this.state.conversation.id,
                message,
                context.module
            );

            if (assistantMessage) {
                this.state.messages.push(assistantMessage);

                // Update conversation from service
                const updatedConv = this.aiAssistant.getCurrentConversation();
                if (updatedConv) {
                    this.state.conversation = updatedConv;
                }

                this.scrollToBottom();
            } else {
                this.state.error = "Failed to get response";
            }
        } catch (error) {
            console.error("Error sending message:", error);
            this.state.error = "An error occurred";
        } finally {
            this.state.isLoading = false;
        }
    }

    /**
     * Handle input key press
     */
    onInputKeyPress(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.sendMessage();
        }
    }

    /**
     * Scroll messages to bottom
     */
    scrollToBottom() {
        setTimeout(() => {
            if (this.messagesEndRef.el) {
                this.messagesEndRef.el.scrollIntoView({ behavior: "smooth" });
            }
        }, 50);
    }

    /**
     * Get current context (module, model, record)
     */
    getCurrentContext() {
        // Try to get context from current action
        // This is a simplified version - you might need to adjust based on your needs
        const context = {
            module: null,
            model: null,
            recordId: null,
        };

        try {
            // Get action service to determine current context
            const currentAction = this.action.currentController?.action;
            if (currentAction) {
                context.model = currentAction.res_model;
                context.recordId = currentAction.res_id;

                // Try to infer module from model
                if (context.model) {
                    if (context.model.startsWith("sale.")) {
                        context.module = "sale";
                    } else if (context.model.startsWith("crm.")) {
                        context.module = "crm";
                    } else if (context.model.startsWith("account.")) {
                        context.module = "account";
                    } else if (context.model.startsWith("stock.")) {
                        context.module = "stock";
                    }
                }
            }
        } catch (error) {
            console.debug("Could not determine context:", error);
        }

        return context;
    }

    /**
     * Format message timestamp
     */
    formatTime(dateString) {
        if (!dateString) return "";
        const date = new Date(dateString);
        return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    }

    /**
     * View all conversations
     */
    viewConversations() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "My Conversations",
            res_model: "ai.conversation",
            views: [[false, "list"], [false, "form"]],
            domain: [["user_id", "=", this.env.services.user.userId]],
            context: { search_default_my_conversations: 1 },
        });
        this.closeChat();
    }
}

AIChatWindow.template = "ai_assistant.ChatWindow";

/**
 * AI Chat Window Systray Item
 */
export class AIChatWindowSystray extends Component {
    setup() {
        this.chatWindow = useRef("chatWindow");
    }

    onClick() {
        if (this.chatWindow.comp) {
            this.chatWindow.comp.toggleChat();
        }
    }
}

AIChatWindowSystray.template = "ai_assistant.ChatWindowSystray";
AIChatWindowSystray.components = { AIChatWindow };

// Register in systray
registry.category("systray").add("AIChatWindowSystray", {
    Component: AIChatWindowSystray,
    isDisplayed: (env) => true,
});
