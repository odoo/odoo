import { Component } from '@odoo/owl';


/**
 * @typedef {Object} WarningNotificationType
 * @property {String} warningMessage
 */
export class WarningNotification extends Component {
    static template = 'website_sale.warningNotification';
    /** @type { WarningNotificationType } */
    static props = {
        warningMessage: String,
    }
}
