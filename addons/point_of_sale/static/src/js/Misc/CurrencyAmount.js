/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";
import Registries from "@point_of_sale/js/Registries";

class CurrencyAmount extends PosComponent {}
CurrencyAmount.template = "CurrencyAmount";

Registries.Component.add(CurrencyAmount);

export default CurrencyAmount;
