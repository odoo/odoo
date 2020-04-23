odoo.define('hr_timesheet.timesheet_kanban_view', function (require) {
"use strict";

const core = require('web.core');

const KanbanColumn = require('web.KanbanColumn');
const KanbanController = require('web.KanbanController');
const KanbanRenderer = require('web.KanbanRenderer');
const KanbanView = require('web.KanbanView');
const viewRegistry = require('web.view_registry');

const qweb = core.qweb;

/**
 * Generate a random integer between 0 and `max`
 * @param {integer} max 
 */
function randInt(max) {
    return Math.floor(Math.random() * max);
}

function renderDemoRecord(record) {
    const template = 'TimesheetGridKanban.DemoRecord';
    return $(qweb.render(template, record || generateDemoRecord()));
}

function generateDemoRecord() {
    return {
        user: 'user' + randInt(4),
        title: 25 + (randInt(5) * 15),
        task: 15 + (randInt(5) * 15),
        duration: '0' + randInt(9),
        running: randInt(10) > 7,
    }
}

/**
 * @override the KanbanColumn to generate fake transparent records if there are none
 */
const TimesheetKanbanColumn = KanbanColumn.extend({
    start() {
        this._super.apply(this, arguments);

        let defs = [];
        let empty = !this.getParent().state.count;
        if (empty) {
            let demoRecords = this.getParent().demo_records;

            if(!demoRecords[this.id]) {
                const numRecords = randInt(3);
                demoRecords[this.id] = [];

                for(let i = 0; i <= numRecords; i++) {
                    demoRecords[this.id].push(generateDemoRecord());
                }
            }

            demoRecords[this.id].forEach((record) => {
                let prom = renderDemoRecord(record).insertAfter(this.$header);
                defs.push(prom)
            });
        }

        return Promise.all(defs);
    },
});

/**
 * @override the KanbanController to add a trigger when a timer is launched or stopped
 */
const TimesheetKanbanController = KanbanController.extend({
    custom_events: _.extend({}, KanbanController.prototype.custom_events, {
        'timer_changed': '_onTimerChanged',
    }),
    /**
     * When a timer is launched or stopped, we reload the view to see the updating.
     * @param {Object} event
     */
    _onTimerChanged: function (event) {
        this.reload();
    }
});

/**
 * @override the KanbanRenderer to generate fake transparent records if there are none
 */
const TimesheetKanbanRenderer = KanbanRenderer.extend({
    config: _.extend({}, KanbanRenderer.prototype.config, {
        KanbanColumn: TimesheetKanbanColumn,
    }),

    init() {
        this._super.apply(this, arguments);
        this.demo_records = {};
    },

    _renderGhostDivs(fragment, nbDivs, options) {
        let defs = [];
        let empty = !this.state.count;
        let demo_records = this.demo_records;

        if(empty) {
            if(!demo_records[0]) {
                demo_records[0] = [];

                for(let i = 0; i < nbDivs; i++) {
                    demo_records[0].push(generateDemoRecord());
                }
            }

            demo_records[0].forEach((record) => {
                defs.push(renderDemoRecord(record).appendTo(fragment));
            });
        }

        defs.push(this._super.apply(this, arguments));
        return Promise.all(defs);
    },
});

const TimesheetKanbanView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Controller: TimesheetKanbanController,
        Renderer: TimesheetKanbanRenderer,
    })
});

viewRegistry.add('timesheet_kanban_view', TimesheetKanbanView);

return { TimesheetKanbanController, TimesheetKanbanView };

});
