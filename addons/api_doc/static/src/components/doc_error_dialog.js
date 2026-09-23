/** @odoo-module native */
import { Component, useState, xml } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";

export class DocErrorDialog extends Component {
    static template = xml`
        <div class="alert error mt-1 d-flex flex-column" role="alert">
            <div class="d-flex align-items-center mb-2">
                <i class="pe-2 fa-solid fa-exclamation-triangle fa-lg" aria-hidden="true"/>
                <h5 class="m-0 text-danger">
                    <t t-out="this.title"/>: <strong t-out="this.props.name"/>
                </h5>
            </div>
            <t t-if="this.traceback">
                <div t-if="this.state.showTraceback" class="overflow-auto position-relative" style="max-height: 500px;">
                    <button
                        class="btn bg-100 position-absolute top-0 end-0"
                        t-ref="copyButton"
                        t-on-click="this.onClickClipboard"
                    >
                        <span class="fa-solid fa-paste"/>
                    </button>
                    <pre class="small text-break p-4" t-out="this.traceback"/>
                </div>
                <button
                    class="btn btn-sm mt-2 align-self-center"
                    t-on-click="this.toggleTraceback"
                    t-out="this.state.showTraceback ? 'Hide Details' : 'Show Technical Details'"
                />
            </t>
        </div>
    `;
    static props = {
        name: { type: String },
        // What failed, so a single model's failure is not reported as "error
        // while loading models" with no way to tell which one.
        subject: { type: String, optional: true },
        status: { type: [Number, { value: null }], optional: true },
        // tryFetch puts the caught exception here when the failure was not an
        // HTTP one, so this is not always a string.
        traceback: { optional: true },
    };

    setup() {
        this.state = useState({
            showTraceback: false,
        });
    }

    get title() {
        return this.props.subject
            ? `Error while loading ${this.props.subject}`
            : "Error while loading models";
    }

    get traceback() {
        const traceback = this.props.traceback;
        if (!traceback) {
            return "";
        }
        return traceback instanceof Error
            ? (traceback.stack ?? String(traceback))
            : String(traceback);
    }

    toggleTraceback() {
        this.state.showTraceback = !this.state.showTraceback;
    }

    onClickClipboard() {
        // `props.message` and `this.contextDetails` never existed: this used to
        // copy the word "undefined" twice into the reader's clipboard.
        const status = this.props.status ? ` (HTTP ${this.props.status})` : "";
        browser.navigator.clipboard.writeText(
            `${this.title}: ${this.props.name}${status}\n\n${this.traceback}`,
        );
    }
}
