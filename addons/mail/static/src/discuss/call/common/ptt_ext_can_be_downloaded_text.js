/* @odoo-module */

import { markup, Component, xml } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { escape, sprintf } from "@web/core/utils/strings";

export class PttExtCanBeDownloadedText extends Component {
    static template = xml`
        <span class="small" t-out="text"/>
    `;

    setup() {
        this.pttExtService = useService("discuss.ptt_extension");
    }

    get text() {
        const translation = _t(
            `The Push-to-Talk feature is only accessible within tab focus. To enable the Push-to-Talk functionality outside of this tab, we recommend downloading our %(anchor_start)sextension%(anchor_end)s.`
        );
        return markup(
            sprintf(escape(translation), {
                anchor_start: `<a href="${this.pttExtService.downloadURL}" target="_blank" class="text-reset text-decoration-underline">`,
                anchor_end: "</a>",
            })
        );
    }
}
