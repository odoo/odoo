import { Component } from "@odoo/owl";
import { BadgeExtraPrice } from "../badge_extra_price/badge_extra_price";

export class ProductCard extends Component {
    static template = "sale.ProductCard";
    static components = { BadgeExtraPrice };
    static props = {
        id: Number,
        name: String,
        extraPrice: Number,
        onClick: Function,
    };
}
