/** @odoo-module */

import { registry } from "@web/core/registry";
import { charField, CharField } from "@web/views/fields/char/char_field";
import { useService } from "@web/core/utils/hooks";
import { Component, useEffect, useRef, useState, markup } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

/**
 * FontAwesome Icon Selection Dialog Component
 */

class IconSelectionDialog extends Component {
  static template = "fa_icon_widget.IconSelectionDialog";
  static components = { Dialog };
  static props = {
    close: Function,
    icons: Array,
    onIconSelected: Function,
  };

  setup() {
    this.searchInputRef = useRef("searchInput");
    this.state = useState({
      selectedIcon: null,
      searchTerm: "",
      filteredIcons: this.props.icons,
    });

    useEffect(
      () => {
        this.filterIcons();
      },
      () => [this.state.searchTerm],
    );
  }

  filterIcons() {
    if (!this.state.searchTerm) {
      this.state.filteredIcons = this.props.icons;
      return;
    }

    const searchTerm = this.state.searchTerm.toLowerCase();
    const iconClass = searchTerm.startsWith("fa-")
      ? searchTerm
      : `fa-${searchTerm}`;
    this.state.filteredIcons = this.props.icons.filter((icon) =>
      icon.toLowerCase().includes(searchTerm),
    );
  }

  onSearch(ev) {
    this.state.searchTerm = ev.target.value;
  }

  onIconClick(icon) {
    this.state.selectedIcon = this.state.selectedIcon === icon ? null : icon;
  }

  onSelectClick() {
    if (this.state.selectedIcon) {
      this.props.onIconSelected(this.state.selectedIcon);
      this.props.close();
    }
  }

  onAddCustomIcon() {
    const customIcon = this.searchInputRef.el.value.trim();
    if (customIcon) {
      // Extract icon name if user entered full class like "fa fa-icon"
      const iconName = customIcon.replace(/^fa\s+fa-/, "");
      this.props.onIconSelected(iconName);
      this.props.close();
    }
  }
}

/**
 * FontAwesome Icon Field Component
 */
export class FaIconField extends CharField {
  static template = "fa_icon_widget.FaIconField";
  static components = { IconSelectionDialog };

  setup() {
    super.setup();
    this.notification = useService("notification");
    this.dialogService = useService("dialog");

    // List of FontAwesome icons to display in the selection dialog
    this.icons = [
      "address-book",
      "handshake-o",
      "area-chart",
      "telegram",
      "car",
      "university",
      "calendar-times-o",
      "bar-chart",
      "commenting-o",
      "star-half-o",
      "dot-circle-o",
      "tachometer",
      "credit-card-alt",
      "money",
      "line-chart",
      "pie-chart",
      "check-square-o",
      "users",
      "shopping-cart",
      "truck",
      "user-circle-o",
      "user-plus",
      "sun-o",
      "paper-plane",
      "wrench",
      "gears",
      "check",
      "download",
      "thermometer-three-quarters",
      "balance-scale",
      "bell",
      "cogs",
      "clone",
      "code",
      "plane",
      "hourglass-half",
      "lock",
      "low-vision",
      "quote-right",
      "exclamation-triangle",
      "volume-control-phone",
      "refresh",
      "sliders",
      "sitemap",
      "toggle-on",
      "wifi",
      "trophy",
      "ticket",
    ];
  }

  /**
   * Get the current icon value as HTML
   * @returns {string} HTML representation of the icon
   */
  iconHtml() {
    this.props.value = this.props.record.data[this.props.name];
    if (!this.props.value) {
      return "";
    }

    // If the value is already HTML (from previous selection), return it
    if (this.props.value) {
      return markup(this.props.value);
    }

    // Otherwise, create the HTML for the icon
    return "";
  }

  /**
   * Get the current icon class
   * @returns {string} CSS class for the icon
   */
  get iconClass() {
    if (!this.props.value) {
      return "";
    }

    // If the value is already HTML, extract the class
    if (this.props.value.includes("<span")) {
      const match = this.props.value.match(/class="([^"]+)"/);
      return match ? match[1] : "";
    }

    // Otherwise, return the fa class
    return `fa fa-${this.props.value}`;
  }

  /**
   * Open the icon selection dialog
   */
  openIconDialog() {
    this.dialogService.add(IconSelectionDialog, {
      icons: this.icons,
      onIconSelected: (icon) => this.onIconSelected(icon),
    });
  }

  /**
   * Handle icon selection
   * @param {string} icon - The selected icon name
   */
  async onIconSelected(icon) {
    // Update the field value with the selected icon
    await this.props.record.update({
      [this.props.name]: `<span class="fa fa-${icon} fa-2x"></span>`,
    });

    // If autosave is enabled, save the record
    if (this.props.autosave) {
      await this.props.record.save();
    }
  }

  /**
   * Clear the selected icon
   */
  async clearIcon() {
    await this.props.record.update({ [this.props.name]: false });

    if (this.props.autosave) {
      await this.props.record.save();
    }
  }
}

export const faIconField = {
  ...charField,
  component: FaIconField,
};

registry.category("fields").add("fa_icon_widget", faIconField);
