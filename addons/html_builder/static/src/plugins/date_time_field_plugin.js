import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { formatDate, formatDateTime, parseDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";

const { DateTime } = luxon;

export class FieldDateTimeAction extends BuilderAction {
    static id = "fieldDateTime";
    getValue({ editingElement }) {
        const dateTime = editingElement.dataset.modifiedDate
            ? editingElement.textContent
            : // If there is no date, oeOriginal is not set and
            // oeOriginalWithFormat contains the format
            editingElement.dataset.oeOriginal
            ? editingElement.dataset.oeOriginalWithFormat
            : "";
        return dateTime && parseDateTime(dateTime).toUnixInteger().toString();
    }
    apply({ editingElement, value }) {
        const format = { date: formatDate, datetime: formatDateTime }[
            editingElement.dataset.oeType
        ];
        editingElement.dataset.modifiedDate = "true";
        editingElement.textContent = format(DateTime.fromSeconds(parseInt(value)));
    }
}

export class DateTimeFieldOption extends BaseOptionComponent {
    static id = "date_time_field_option";
    static template = "html_builder.DateTimeFieldOption";
    setup() {
        super.setup();
        this.state = useDomState((el) => ({ fieldType: el.dataset.oeType }));
    }
}

registry.category("builder-options").add(DateTimeFieldOption.id, DateTimeFieldOption);

export class DateTimeFieldPlugin extends Plugin {
    static id = "dateTimeField";
    /** @type {import("plugins").BuilderResources} */
    resources = {
        content_not_editable_selectors:
            "[data-oe-field][data-oe-type=date], [data-oe-field][data-oe-type=datetime]",
        builder_actions: { FieldDateTimeAction },
    };
}
registry.category("builder-plugins").add(DateTimeFieldPlugin.id, DateTimeFieldPlugin);
