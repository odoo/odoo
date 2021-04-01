/** @odoo-module **/

import { useService } from "../core/hooks";

const { Component } = owl;

export class Notification extends Component {
  setup() {
    this.notificationService = useService("notification");
  }

  get icon() {
    switch (this.props.type) {
      case "danger":
        return "fa-exclamation";
      case "warning":
        return "fa-lightbulb-o";
      case "success":
        return "fa-check";
      case "info":
        return "fa-info";
      default:
        return this.props.icon;
    }
  }

  get className() {
    let className;
    switch (this.props.type) {
      case "danger":
        className = "bg-danger";
        break;
      case "warning":
        className = "bg-warning";
        break;
      case "success":
        className = "bg-success";
        break;
      case "info":
        className = "bg-info";
        break;
    }
    return className ? `${className} ${this.props.className}` : this.props.className;
  }
}

Notification.template = "wowl.Notification";
Notification.props = {
  id: { type: Number },
  message: { type: String },
  title: { type: String, optional: true },
  type: {
    type: String,
    optional: true,
    validate: (t) => ["warning", "danger", "success", "info"].includes(t),
  },
  className: { type: String, optional: true },
  icon: { type: String, optional: true },
  buttons: {
    type: Array,
    element: {
      type: Object,
      shape: {
        name: { type: String },
        icon: { type: String, optional: true },
        primary: { type: Boolean, optional: true },
      },
    },
  },
};
Notification.defaultProps = {
  buttons: [],
  className: "",
  type: "warning",
};
