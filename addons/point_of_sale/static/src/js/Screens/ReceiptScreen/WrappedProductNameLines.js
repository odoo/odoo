/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";
import Registries from "@point_of_sale/js/Registries";

class WrappedProductNameLines extends PosComponent {}
WrappedProductNameLines.template = "WrappedProductNameLines";

Registries.Component.add(WrappedProductNameLines);

export default WrappedProductNameLines;
