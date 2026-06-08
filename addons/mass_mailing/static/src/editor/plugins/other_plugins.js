import { AutofocusPlugin } from "@html_editor/others/autofocus_plugin";
import { registry } from "@web/core/registry";

registry.category("basic-editor-plugins").add(AutofocusPlugin.id, AutofocusPlugin);
