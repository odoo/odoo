import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { formatDate, formatDateTime, parseDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";

const { DateTime } = luxon;

const dateAndDatetimeFieldSelector =
    "[data-oe-field][data-oe-type=date], [data-oe-field][data-oe-type=datetime]";

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
    static template = "html_builder.DateTimeFieldOption";
    static selector = dateAndDatetimeFieldSelector;
    setup() {
        super.setup();
        this.state = useDomState((el) => ({ fieldType: el.dataset.oeType }));
    }
}

export class DateTimeFieldPlugin extends Plugin {
    static id = "dateTimeField";
    /** @type {import("plugins").BuilderResources} */
    resources = {
        content_not_editable_selectors: dateAndDatetimeFieldSelector,
        builder_options: DateTimeFieldOption,
        builder_actions: { FieldDateTimeAction },
    };
}
registry.category("builder-plugins").add(DateTimeFieldPlugin.id, DateTimeFieldPlugin);
