odoo.define('project.project_kanban_column', function (require) {
    "use strict";

    var core = require('web.core');
    var KanbanColumn = require('web.KanbanColumn');

    var qweb = core.qweb;

    var ProjectKanbanColumn = KanbanColumn.extend({
        start() {
            this._super.apply(this, arguments);

            let defs = [];
            let emptyProject = !this.getParent().state.count;
            if (emptyProject) {
                let demoRecords = this.getParent().demo_records;

                if(!demoRecords[this.id]) {
                    const numRecords = Math.floor(Math.random() * 4);
                    demoRecords[this.id] = [];

                    for(let i = 0; i <= numRecords; i++) {
                        demoRecords[this.id].push(this._generateDemoData());
                    }
                }

                demoRecords[this.id].forEach((record) => {
                    defs.push(this._addDemoRecord(record));
                });
            }

            return Promise.all(defs);
        },

        cancelQuickCreate() {
            this._super.apply(this, arguments);

            let emptyProject = !this.getParent().state.count;
            if(!emptyProject) {
                this.$el.find('.o_kanban_demo_record').remove();
            }
        },

        _generateDemoData() {
            let activity = '';
            let status = '';
            let rating = '';

            let rand = Math.random();
            if(rand > 0.9) {
                activity = 'text-success';
            } else if(rand > 0.8) {
                activity = 'text-warning';
            } else if(rand > 0.7) {
                activity = 'text-danger';
            }

            rand = Math.random();
            if(rand > 0.9) {
                status = 'o_status_green';
            } else if(rand > 0.8) {
                status = 'o_status_red';
            }

            rand = Math.random();
            if(rand > 0.9) {
                rating = 'fa-smile-o text-success';
            } else if(rand > 0.8) {
                rating = 'fa-meh-o text-warning';
            } else if(rand > 0.7) {
                rating = 'fa-frown-o text-danger';
            }

            return {
                favorite: Math.random() > 0.3 ? 'fa-star-o' : 'fa-star',
                activity: activity,
                status: status,
                rating: this.getParent().rating_enabled && rating,
                tag: Math.random() < 0.7 ? '' : Math.floor(Math.random() * 11),
                user: 'user' + Math.floor(Math.random() * 4),
                title: 25 + (Math.floor(Math.random() * 5) * 15),
            };
        },

        _addDemoRecord(record_data) {
            const template = 'ProjectKanbanView.DemoRecord';
            let record = $(qweb.render(template, record_data || this._generateDemoData()));

            // Prevents dragging record from column to column
            record.on('mousedown', (evt) => {
                evt.preventDefault();
                evt.stopPropagation();
            });

            return record.insertAfter(this.$header);
        },

        _onDeleteColumn(event) {
            event.preventDefault();
            this.trigger_up('kanban_column_delete_wizard');
        },
    });


    return ProjectKanbanColumn;
});
