import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { PartnerLine } from "@point_of_sale/app/screens/partner_list/partner_line/partner_line";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Input } from "@point_of_sale/app/generic_components/inputs/input/input";
import { Component, useState } from "@odoo/owl";
import { CustomListView } from "@point_of_sale/app/components/custom_list_view/custom_list_view";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class SaleOrderPopup extends Component {
    static components = { PartnerLine, Dialog, Input, CustomListView, Dropdown, DropdownItem };
    static template = "point_of_sale.SaleOrderPopup";

    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
        this.notification = useService("notification");
        this.dialog = useService("dialog");
    }

    clickSaleOrder(so) {
        this.props.getPayload(so);
        this.props.close();
    }
}
