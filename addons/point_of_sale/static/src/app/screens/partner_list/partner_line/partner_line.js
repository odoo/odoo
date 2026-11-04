import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

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
        this.ui = useService("ui");
    }
}
