import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
export class PartnerLine extends Component {
    static template = "point_of_sale.PartnerLine";
    static components = { Dropdown, DropdownItem };
    static props = [
        "close",
        "partner",
        "isSelected",
        "isBalanceDisplayed",
        "onClickEdit",
        "onClickUnselect",
        "onClickPartner",
        "onClickOrders",
    ];

    setup() {
        this.pos = usePos();
        this.ui = useService("ui");
    }
}
