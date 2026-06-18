import { Component, props, t } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { ResPartner } from "@point_of_sale/app/models/res_partner";

export class PartnerLine extends Component {
    static template = "point_of_sale.PartnerLine";
    static components = { Dropdown, DropdownItem };
    props = props({
        close: t.function(),
        partner: t.instanceOf(ResPartner),
        isSelected: t.boolean(),
        isBalanceDisplayed: t.boolean(),
        onClickEdit: t.function(),
        onClickUnselect: t.function(),
        onClickPartner: t.function(),
        onClickOrders: t.function(),
    });

    setup() {
        this.pos = usePos();
        this.ui = useService("ui");
    }
}
