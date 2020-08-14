odoo.define('note.systray.ActivityMenu', function (require) {
"use strict";

const ActivityMenu = require('mail.systray.ActivityMenu');
const { ComponentAdapter } = require("web.OwlCompatibility");
const datepicker = require('web.datepicker');

    class FieldWidgetAdapter extends ComponentAdapter {
        constructor(parent, props) {
            props.Component = props.widget;
            super(...arguments);
        }

        get widgetArgs() {
            return [this.props.options];
        }
    }

    ActivityMenu.patch("note.systray.ActivityMenu", (T) => {
        class NoteActivityMenu extends T {
            //--------------------------------------------------
            // Private
            //--------------------------------------------------
            /**
             * Moving notes at first place
             * @override
             */
            async _getActivityData() {
                await super._getActivityData(...arguments);
                const reminderIndex = _.findIndex(this.state.activities, function (val) {
                    return val.model === "note.note";
                });
                if (reminderIndex > 0) {
                    this.state.activities.splice(0, 0, this.state.activities.splice(reminderIndex, 1)[0]);
                }
            }
            /**
             * Save the note to database using datepicker date and field as note
             * By default, when no datetime is set, it uses the current datetime.
             *
             * @private
             */
            async _saveNote() {
                const note = this.el.querySelector(".o_note_input").value.trim();
                if (!note) {
                    return;
                }
                let params = { note: note };
                const noteDateTime = this.noteDateTimeWidget.getValue();
                if (noteDateTime) {
                    params = Object.assign(params, { date_deadline: noteDateTime });
                } else {
                    params = Object.assign(params, { date_deadline: moment() });
                }
                this.el.querySelector(".o_note_show").classList.remove("d-none");
                this.el.querySelector(".o_note").classList.add("d-none");
                await this.env.services
                    .rpc({
                        route: "/note/new",
                        params: params,
                    })
                    .then(this._updateActivityPreview.bind(this));
            }
            //-----------------------------------------
            // Handlers
            //-----------------------------------------
            /**
             * @override
             */
            _onActivityFilterClick(ev) {
                const el = ev.currentTarget;
                if (!el.classList.contains("o_note")) {
                    const data = Object.assign({}, el.dataset, ev.target.dataset);
                    if (data.res_model === "note.note" && data.filter === "my") {
                        this.env.bus.trigger("do-action", {
                            action: {
                                type: "ir.actions.act_window",
                                name: data.model_name,
                                res_model: data.res_model,
                                views: [
                                    [false, "kanban"],
                                    [false, "form"],
                                    [false, "list"],
                                ],
                            },
                        });
                    } else {
                        super._onActivityFilterClick(...arguments);
                    }
                }
            }
            /**
             * When add new note button clicked, toggling quick note create view inside
             * Systray activity view
             *
             * @private
             * @param {MouseEvent} ev
             */
            async _onAddNoteClick(ev) {
                if (!this.noteDateTimeWidget) {
                    this.noteDateTimeWidgetAdapter = new FieldWidgetAdapter(this, {
                        options: { useCurrent: true },
                        widget: datepicker.DateWidget,
                    });
                }
                await this.noteDateTimeWidgetAdapter
                    .mount(this.el.querySelector(".o_note_datetime"));
                this.noteDateTimeWidget = this.noteDateTimeWidgetAdapter.widget;
                this.noteDateTimeWidget.$input.attr("placeholder", this.env._t("Today"));
                this.noteDateTimeWidget.setValue(false);
                this.el.querySelector(".o_note_show").classList.toggle("d-none");
                this.el.querySelector(".o_note").classList.toggle("d-none");
                this.el.querySelector(".o_note_input").value = "";
                this.el.querySelector(".o_note_input").focus();
            }
            /**
             * When focusing on input for new quick note systerm tray must be open.
             * Preventing to close
             *
             * @private
             * @param {MouseEvent} ev
             */
            _onNewNoteClick(ev) {
            }
            /**
             * Opens datetime picker for note.
             * Quick FIX due to no option for set custom icon instead of caret in datepicker.
             *
             * @private
             * @param {MouseEvent} ev
             */
            _onNoteDateTimeSetClick(ev) {
                this.noteDateTimeWidget.$input.click();
            }
            /**
             * Saving note (quick create) and updating activity preview
             *
             * @private
             * @param {MouseEvent} ev
             */
            async _onNoteSaveClick(ev) {
                await this._saveNote();
            }
            /**
             * Handling Enter key for quick create note.
             *
             * @private
             * @param {KeyboardEvent} ev
             */
            async _onNoteInputKeyDown(ev) {
                if (ev.which === $.ui.keyCode.ENTER) {
                    await this._saveNote();
                }
            }
        }

        return NoteActivityMenu;
    });
});
