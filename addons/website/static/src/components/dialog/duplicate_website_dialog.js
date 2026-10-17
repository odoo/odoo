import { Component, proxy, signal, t, useProps } from "@odoo/owl";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { WebsiteDialog } from "./dialog";

export class DuplicateWebsiteDialog extends Component {
    static components = { WebsiteDialog };
    static template = "website.DuplicateWebsiteDialog";
    props = useProps({
        onDuplicate: t.function(),
        close: t.function(),
        websiteIds: t.array(t.number()),
    });
    autofocusRef = signal.ref();

    setup() {
        this.orm = useService("orm");
        useAutofocus({ ref: this.autofocusRef });

        this.state = proxy({
            name: "",
        });
    }

    async duplicate(ev) {
        ev.currentTarget.disabled = true;
        const name = this.state.name.trim();
        try {
            for (let count = 0; count < this.props.websiteIds.length; count++) {
                await this.orm.call("website", "copy", [[this.props.websiteIds[count]]], {
                    default: { name: name + (count ? ` ${count + 1}` : "") },
                });
            }
        } finally {
            this.props.onDuplicate();
            this.props.close();
        }
    }
}
