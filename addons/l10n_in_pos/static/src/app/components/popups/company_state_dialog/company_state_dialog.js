import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { Dialog } from "@web/ui/dialog/dialog";
export class companyStateDialog extends Component {
    static components = { Dialog };
    static template = "l10n_in_pos.companyStateDialog";
    static props = {
        close: Function,
    };

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
