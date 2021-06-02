/** @odoo-module alias=point_of_sale.SelectionPopup **/

import Draggable from 'point_of_sale.Draggable';
import { _t } from 'web.core';

/**
 * @param {Object} props
 * @param {string} [props.cancelText='Cancel']
 * @param {string} [props.title='Select']
 * @param {{ id: string, label: string, isSelected: boolean}[]} [props.list=[]]
 */
class SelectionPopup extends owl.Component {}
SelectionPopup.components = { Draggable };
SelectionPopup.template = 'point_of_sale.SelectionPopup';
SelectionPopup.defaultProps = {
    cancelText: _t('Cancel'),
    title: _t('Select'),
    list: [],
};

export default SelectionPopup;
