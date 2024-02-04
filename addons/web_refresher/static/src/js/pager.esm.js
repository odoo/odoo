/** @odoo-module **/
/* Copyright 2022 Tecnativa - Carlos Roca
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */
import {Pager} from "@web/core/pager/pager";
import {Refresher} from "./refresher.esm";

Pager.components = Object.assign({}, Pager.components, {
    Refresher,
});
