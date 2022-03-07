/** @odoo-module **/

import Orderline from 'point_of_sale.Orderline';
import Registries from 'point_of_sale.Registries';

export const PosLoyaltyOrderline = (Orderline) =>
    class extends Orderline{
        get addedClasses() {
            return Object.assign({'program-reward': this.props.line.is_reward_line}, super.addedClasses);
        }
    };

Registries.Component.extend(Orderline, PosLoyaltyOrderline);
