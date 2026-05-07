import { Component, signal, t, useProps, xml } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";

export class DocCopyablePre extends Component {
    static template = xml`
        <div class="o-doc-copyable d-flex flex-nowrap align-items-start gap-2" t-att-class="this.props.class">
            <pre class="flex-fill" t-out="this.props.value"/>
            <button
                class="o-doc-copy-btn d-flex align-items-center flex-shrink-0"
                t-att-class="{ 'o-doc-copied': this.copied() }"
                t-on-click="this.copy"
                type="button"
                t-att-title="this.copied() ? 'Copied!' : 'Copy'"
            >
                <i class="oi" t-att-data-icon="this.copied() ? 'check' : 'assignment'" aria-hidden="true"/>
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
