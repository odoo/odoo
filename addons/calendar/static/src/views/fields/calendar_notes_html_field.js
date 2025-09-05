import { registry } from "@web/core/registry";
import { htmlField, HtmlField } from "@html_editor/fields/html_field";
import { MoveNodePlugin } from "@html_editor/main/movenode_plugin";

class CalendarEventNotesHtmlField extends HtmlField {
    getConfig() {
        const config = super.getConfig();
        config.Plugins = config.Plugins.filter((plugin) => plugin !== MoveNodePlugin);
        return config;
    }
}

export const calendarEventNotesHtmlField = { ...htmlField, component: CalendarEventNotesHtmlField };
registry.category("fields").add("calendar_event_notes_html", calendarEventNotesHtmlField);
