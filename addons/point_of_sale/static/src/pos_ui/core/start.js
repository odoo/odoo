/** @odoo-module */

import { startWebClient } from "@web/start";
import { PosApp } from "./pos_app/pos_app";
import Registries from "point_of_sale.Registries";

Registries.Component.freeze();
Registries.Model.freeze();
startWebClient(PosApp);
