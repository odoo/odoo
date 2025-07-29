/** @odoo-module **/

// Importamos el componente Popover que es el que realmente genera las horas
import { FloatTimeSelectionPopover } from "@hr_holidays/components/float_time_selection/float_time_selection_popover";
import { FloatTimeSelectionField } from "@hr_holidays/components/float_time_selection/float_time_selection";
import { patch } from "@web/core/utils/patch";

patch(FloatTimeSelectionPopover.prototype, {
  setup() {
    super.setup();

    const availableHours12h = [];
    for (let h = 0; h < 24; h++) {
      const hour_float = h;
      let hour_12 = h % 12;
      if (hour_12 === 0) {
        hour_12 = 12;
      }
      const ampm = h < 12 ? "AM" : "PM";
      const label = `${String(hour_12).padStart(2, "0")} ${ampm}`;

      availableHours12h.push([hour_float, label]);
    }

    this.availableHours = availableHours12h;
  },
});

patch(FloatTimeSelectionField.prototype, {
  get formattedValue() {
    const floatValue = this.props.record.data[this.props.name];
    const hours24 = Math.floor(floatValue);
    const minutes = Math.round((floatValue - hours24) * 60);

    let hours12 = hours24 % 12;
    if (hours12 === 0) {
      hours12 = 12;
    }
    const ampm = hours24 < 12 ? "AM" : "PM";

    const hoursStr = String(hours12).padStart(2, "0");
    const minutesStr = String(minutes).padStart(2, "0");

    return `${hoursStr}:${minutesStr} ${ampm}`;
  },
});
