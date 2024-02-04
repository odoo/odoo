/** @odoo-module **/
/* Copyright 2022 Tecnativa - Alexandre D. Díaz
 * Copyright 2022 Tecnativa - Carlos Roca
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */

const {Component} = owl;

export class Refresher extends Component {
    _doRefresh() {
        // Note: here we use the pager props, see xml
        const {limit, offset} = this.props;
        this.props.onUpdate({offset, limit});
    }
}

Refresher.template = "web_refresher.Button";
