/** @odoo-module **/

import { QrOrderButton } from "@pos_self_order/overrides/components/qr_order_button/qr_order_button";
import { FloorScreen } from "@pos_restaurant/app/floor_screen/floor_screen";

FloorScreen.components = { ...FloorScreen.components, QrOrderButton };
