import { Dialog } from "@web/core/dialog/dialog";
import { Component, props, t } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

export class companyStateDialog extends Component {
    static components = { Dialog };
    static template = "l10n_in_pos.companyStateDialog";
    props = props({
        close: t.function(),
    });

    setup() {
        this.pos = usePos();
    }

    redirect() {
        window.location = "/odoo/companies/" + this.pos.company.id;
    }

    onClose() {
        this.props.close();
    }
}
