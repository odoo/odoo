/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component, useState, onWillStart } = owl;

export class VendAIOnboarding extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.state = useState({
            currentStep: 0,
            steps: [
                {
                    title: "Welcome to VendAI",
                    description: "Let's set up your shop in just a few steps",
                    completed: false
                },
                {
                    title: "Shop Details",
                    description: "Tell us about your shop",
                    completed: false
                },
                {
                    title: "Add Products",
                    description: "Import your products or add them manually",
                    completed: false
                },
                {
                    title: "Ready to Sell",
                    description: "Your POS is ready to use",
                    completed: false
                }
            ]
        });

        onWillStart(async () => {
            const state = await this.rpc("/web/vendai/onboarding");
            this._updateStepsFromState(state);
        });
    }

    async nextStep() {
        if (this.state.currentStep < this.state.steps.length - 1) {
            const step = this.state.steps[this.state.currentStep];
            await this.rpc("/web/vendai/onboarding/complete", {
                step: step.id
            });
            step.completed = true;
            this.state.currentStep += 1;
        }
    }

    _updateStepsFromState(state) {
        if (state.shop_configured) {
            this.state.steps[1].completed = true;
            if (!this.state.steps[2].completed) {
                this.state.currentStep = 2;
            }
        }
        if (state.has_products) {
            this.state.steps[2].completed = true;
            if (!this.state.steps[3].completed) {
                this.state.currentStep = 3;
            }
        }
    }
}
