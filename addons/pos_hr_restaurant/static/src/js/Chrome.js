/* @odoo-module alias=pos_restaurant_hr.chrome */

import Chrome from '@point_of_sale/js/Chrome';
import Registries from '@point_of_sale/js/Registries';


export const PosHrRestaurantChrome = (Chrome) => class extends Chrome {
    //@override
    _shouldResetIdleTimer() {
        return super._shouldResetIdleTimer() && this.tempScreen.name !== 'LoginScreen';
    }
}

Registries.Component.extend(Chrome, PosHrRestaurantChrome);
