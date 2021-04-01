/** @odoo-module **/

export default class OdooError extends Error {
  constructor(name) {
    super();
    this.name = name;
  }
}
