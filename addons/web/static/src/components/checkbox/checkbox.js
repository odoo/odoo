/** @odoo-module **/

const { loadBundle } = require('web.ajax');
const assets_mixed = loadBundle('web.assets_mixed');

const { Component, QWeb } = owl;

/**
 * Custom checkbox
 *
 * <CheckBox
 *    value="boolean"
 *    disabled="boolean"
 *    t-on-change="_onValueChange"
 *    >
 *    Change the label text
 *  </CheckBox>
 *
 * @extends Component
 */

export class CheckBox extends Component {
  _id = `checkbox-comp-${CheckBox.nextId++}`;
}

CheckBox.template = "web.CheckBox";
CheckBox.nextId = 1;

QWeb.registerComponent("CheckBox", CheckBox);
