import { Component, useState, xml } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";

export class DocErrorDialog extends Component {
    static template = xml`
        <div class="alert error mt-1 d-flex flex-column" role="alert">
            <div class="d-flex align-items-center mb-2">
                <i class="pe-2 fa fa-exclamation-triangle fa-lg" aria-hidden="true"/>
                <h5 class="m-0 text-danger">Error while loading models: <strong t-out="props.name"/></h5>
            </div>
            <t t-if="props.traceback">
                <div t-if="state.showTraceback" class="overflow-auto position-relative" style="max-height: 500px;">
                    <button
                        class="btn bg-100 position-absolute top-0 end-0"
                        t-ref="copyButton"
                        t-on-click="onClickClipboard"
                    >
                        <span class="fa fa-clipboard"/>
                    </button>
                    <pre class="small text-break p-4" t-out="props.traceback"/>
                </div>
                <button
                    class="btn btn-sm mt-2 align-self-center"
                    t-on-click="toggleTraceback"
                    t-out="state.showTraceback ? 'Hide Details' : 'Show Technical Details'"
                />
            </t>
        </div>
    `;
    static props = {
        name: {type: String},
        status: {type: Number, optional: true},
        traceback: {type: String, optional: true},
    };

    setup() {
        this.state = useState({
            showTraceback: false
        });
    }

    toggleTraceback() {
        this.state.showTraceback = !this.state.showTraceback;
    }

    onClickClipboard() {
        browser.navigator.clipboard.writeText(
            `${this.props.name}\n\n${this.props.message}\n\n${this.contextDetails}\n\n${this.props.traceback}`
        );
    }
}
