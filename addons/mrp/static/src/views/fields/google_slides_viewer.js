/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CharField, charField } from "@web/views/fields/char/char_field";

const { useState } = owl;

export class SlidesViewer extends CharField {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.page = 1 || this.props.page;
        this.state = useState({
            isValid: true,
        });
    }

    get fileName() {
        return this.state.fileName || this.props.record.data[this.props.name] || "";
    }

    get url() {
        var src = false;
        if (this.props.record.data[this.props.name]) {
            // check given google slide url is valid or not
            var googleRegExp = /(^https:\/\/docs.google.com).*(\/d\/e\/|\/d\/)([A-Za-z0-9-_]+)/;
            var google = this.props.record.data[this.props.name].match(googleRegExp);
            if (google && google[3]) {
                src =
                    "https://docs.google.com/presentation" +
                    google[2] +
                    google[3] +
                    "/preview?slide=" +
                    this.page;
            }
        }
        return src || this.props.value;
    }

    onLoadFailed() {
        this.state.isValid = false;
        this.notification.add(this.env._t("Could not display the selected spreadsheet"), {
            type: "danger",
        });
    }
}

SlidesViewer.template = "mrp.SlidesViewer";

export const slidesViewer = {
    ...charField,
    component: SlidesViewer,
    displayName: _lt("Google Slides Viewer"),
};

registry.category("fields").add("embed_viewer", slidesViewer);
