/** @odoo-module **/

import { useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CharField, charField } from "@web/views/fields/char/char_field";

export function getGoogleSlideUrl(value, page) {
    let url = false;
    const googleRegExp = /(^https:\/\/docs.google.com).*(\/d\/e\/|\/d\/)([A-Za-z0-9-_]+)/;
    const google = value.match(googleRegExp);
    if (google && google[3]) {
        url = `https://docs.google.com/presentation${google[2]}${google[3]}/preview?slide=${page}`;
    }
    return url;
}

export class GoogleSlideViewer extends CharField {
    static template = "web.GoogleSlideViewer";
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.page = 1;
        this.state = useState({
            isValid: true,
        });
    }

    get fileName() {
        return this.state.fileName || this.props.record.data[this.props.name] || "";
    }

    _get_slide_page() {
        return this.props.record.data[this.props.name + "_page"]
            ? this.props.record.data[this.props.name + "_page"]
            : this.page;
    }

    get url() {
        let url = this.props.value;
        if (this.props.record.data[this.props.name]) {
            url = getGoogleSlideUrl(
                this.props.record.data[this.props.name],
                this._get_slide_page()
            );
        }
        return url;
    }

    onLoadFailed() {
        this.state.isValid = false;
        this.notification.add(_t("Could not display the selected spreadsheet"), { type: "danger" });
    }
}

export const googleSlideViewer = {
    ...charField,
    component: GoogleSlideViewer,
    displayName: _t("Google Slide Viewer"),
};

registry.category("fields").add("embed_viewer", googleSlideViewer);
