/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component, useState, onWillStart } = owl;

export class VendAIAssistant extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.state = useState({
            messages: [],
            inputValue: "",
            isLoading: false,
            autonomyLevel: 30, // 0-100 scale
        });

        this.messageHistory = [];
    }

    async sendMessage(event) {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            const message = this.state.inputValue.trim();
            if (!message) return;

            this.state.messages.push({
                content: message,
                type: 'user'
            });
            this.state.inputValue = "";
            this.state.isLoading = true;

            try {
                const response = await this.rpc("/web/vendai/assistant/query", {
                    query: message,
                    context: {
                        autonomy_level: this.state.autonomyLevel,
                        active_model: this.env.model,
                        active_id: this.env.activeIds[0],
                        view_type: this.env.viewType,
                    }
                });

                if (response.success) {
                    this.state.messages.push({
                        content: response.response,
                        type: 'assistant'
                    });
                } else {
                    throw new Error(response.error);
                }
            } catch (error) {
                this.state.messages.push({
                    content: "Sorry, I encountered an error. Please try again.",
                    type: 'error'
                });
            } finally {
                this.state.isLoading = false;
            }
        }
    }

    updateAutonomyLevel(event) {
        this.state.autonomyLevel = parseInt(event.target.value);
    }
}
