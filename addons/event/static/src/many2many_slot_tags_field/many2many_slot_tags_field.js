
import { many2ManyTagsFieldColorEditable } from "@web/views/fields/many2many_tags/many2many_tags_field";
import { registry } from "@web/core/registry";

// The many2many_tags widget only allows the tags edition via a popup in form views.
// Extending it to be able to edit the tags in the form one2many list view.
registry.category("fields").add("many2many_slot_tags", many2ManyTagsFieldColorEditable);
