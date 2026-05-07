import { Component, signal, t, useProps, xml } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";

export class DocCopyablePre extends Component {
    static template = xml`
        <div class="o-doc-copyable position-relative" t-att-class="this.props.class">
            <pre t-out="this.props.value"/>
            <button
                class="o-doc-copy-btn position-absolute top-50 end-0 translate-middle-y me-2 d-flex align-items-center"
                t-on-click="this.copy"
                type="button"
                title="Copy"
            >
                <i t-if="!this.copied()" class="oi" data-icon="assignment" aria-hidden="true"/>
                <span t-else="">Copied!</span>
            </button>
        </div>
    `;

    props = useProps({
        value: t.string(),
        class: t.string().optional(""),
    });

    copied = signal(false);

    copy() {
        browser.navigator.clipboard.writeText(this.props.value);
        this.copied.set(true);
        setTimeout(() => this.copied.set(false), 1000);
    }
}
