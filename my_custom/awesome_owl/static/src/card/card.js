/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

export class Card extends Component {
  // Định nghĩa các props cho Card component
  static props = {
    title: String,
    slots: {
      type: Object,
      shape: {
        default: true
      }
    }
  };

  static template = "awesome_owl.card";

  setup() {
    this.state = useState({ isOpen: true });
  }

  handleToggle() {
    this.state.isOpen = !this.state.isOpen
  }
}
