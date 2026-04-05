/** @odoo-module **/

import { Component, onError, useState, xml } from "@odoo/owl";

/**
 * ErrorBoundary catches rendering errors in its children and displays
 * a fallback UI instead of crashing the entire Odoo action view.
 *
 * Usage:
 *   <ErrorBoundary>
 *       <MyFragileComponent/>
 *   </ErrorBoundary>
 *
 * With custom fallback:
 *   <ErrorBoundary>
 *       <MyChart/>
 *       <t t-set-slot="fallback" t-slot-scope="scope">
 *           <p>Chart failed: <t t-esc="scope.error.message"/></p>
 *           <button t-on-click="scope.retry">Retry</button>
 *       </t>
 *   </ErrorBoundary>
 *
 * Props:
 *   onError(error, info) — optional callback when an error is caught
 */
export class ErrorBoundary extends Component {
    static template = xml`
        <t t-if="state.error">
            <t t-slot="fallback" error="state.error" retry="() => this.retry()">
                <div class="odx-error-boundary" role="alert">
                    <div class="odx-error-boundary__icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="20" height="20">
                            <circle cx="12" cy="12" r="10"/>
                            <line x1="12" y1="8" x2="12" y2="12"/>
                            <line x1="12" y1="16" x2="12.01" y2="16"/>
                        </svg>
                    </div>
                    <div class="odx-error-boundary__body">
                        <span class="odx-error-boundary__title">Something went wrong</span>
                        <span class="odx-error-boundary__message" t-esc="state.error.message"/>
                    </div>
                    <button class="odx-error-boundary__retry" t-on-click="retry">Retry</button>
                </div>
            </t>
        </t>
        <t t-else="">
            <t t-slot="default"/>
        </t>
    `;
    static props = {
        onError: { type: Function, optional: true },
        slots: { type: Object },
    };

    setup() {
        this.state = useState({ error: null });
        onError((error, info) => {
            this.state.error = error;
            if (this.props.onError) {
                this.props.onError(error, info);
            }
            console.error("[ErrorBoundary]", error);
        });
    }

    retry() {
        this.state.error = null;
    }
}
