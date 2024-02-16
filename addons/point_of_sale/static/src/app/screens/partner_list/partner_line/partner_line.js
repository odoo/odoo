import { Component } from "@odoo/owl";

export class PartnerLine extends Component {
    static template = "point_of_sale.PartnerLine";
    static props = [
        "partner",
        "isSelected",
        "isBalanceDisplayed",
        "onClickEdit",
        "onClickUnselect",
        "onClickPartner",
    ];
}
