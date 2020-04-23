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

function generateDemoRecord() {
    const template = 'TimesheetGridKanban.DemoRecord';
    let record = $(qweb.render(template, {
        user: 'user' + randInt(4),
        title: 25 + (randInt(5) * 15),
        task: 15 + (randInt(5) * 15),
        duration: '0' + randInt(9),
        running: randInt(10) > 7,
    }));
    return record;
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
            const numRecords = randInt(3);

            for(let i = 0; i <= numRecords; i++) {
                let prom = generateDemoRecord().insertAfter(this.$header);
                defs.push(prom);
            }
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

    _renderGhostDivs(fragment, nbDivs, options) {
        let defs = [];
        let empty = !this.state.count;
        if (!empty) {
            return this._super_apply(this, arguments);
        }

        for(let i = 0; i < nbDivs; i++) {
            let prom = generateDemoRecord().appendTo(fragment);
            defs.push(prom);
        }

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
