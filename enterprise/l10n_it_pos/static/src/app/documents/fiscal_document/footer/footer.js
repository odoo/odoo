import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { _t } from "@web/core/l10n/translation";
import { formatDateTime } from "@web/core/l10n/dates";
import { parseUTCString } from "@point_of_sale/utils";
import { PrintRecMessage, PrintNormal } from "@l10n_it_pos/app/fiscal_printer/commands";
import { Heading } from "@l10n_it_pos/app/documents/entities";

export class Footer extends Component {
    static template = "l10n_it_pos.FiscalDocumentFooter";

    static components = {
        PrintRecMessage,
        PrintNormal,
    };

    static props = {
        order: {
            type: Object,
            optional: true, // To keep backward compatibility
        },
        isFiscal: {
            type: Boolean,
            optional: true,
        },
    };
    static defaultProps = { isFiscal: true };

    async setup() {
        this.pos = usePos();
        this.order = this.props.order || this.pos.get_order();
    }

    get footers() {
        Heading.resetIndex();
        const headings = [
            new Heading(_t("Powered by Odoo")),
            new Heading(this.order.name),
            new Heading(formatDateTime(parseUTCString(this.order.date_order))),
        ];

        return headings.filter(Boolean);
    }
}
