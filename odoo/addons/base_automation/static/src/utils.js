/** @odoo-module */

export const TRIGGER_FILTERS = {
    on_create_or_write: (f) => true,
    on_create: (f) => true,
    on_write: (f) => true,
    on_change: (f) => true,
    on_unlink: (f) => true,
    on_time: (f) => true,
    on_time_created: (f) => f.ttype === "datetime" && f.name === "create_date",
    on_time_updated: (f) => f.ttype === "datetime" && f.name === "write_date",
    on_stage_set: (f) =>
        f.ttype === "many2one" && ["stage_id", "x_studio_stage_id"].includes(f.name),
    on_user_set: (f) =>
        f.relation === "res.users" &&
        ["many2one", "many2many"].includes(f.ttype) &&
        ["user_id", "user_ids", "x_studio_user_id", "x_studio_user_ids"].includes(f.name),
    on_tag_set: (f) => f.ttype === "many2many" && ["tag_ids", "x_studio_tag_ids"].includes(f.name),
    on_state_set: (f) => f.ttype === "selection" && ["state", "x_studio_state"].includes(f.name),
    on_priority_set: (f) =>
        f.ttype === "selection" && ["priority", "x_studio_priority"].includes(f.name),
    on_archive: (f) => f.ttype === "boolean" && ["active", "x_active"].includes(f.name),
    on_unarchive: (f) => f.ttype === "boolean" && ["active", "x_active"].includes(f.name),
    on_webhook: (f) => true,
};
