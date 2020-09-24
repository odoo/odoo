odoo.define('project.task_kanban_examples', function (require) {
'use strict';

var core = require('web.core');
var kanbanExamplesRegistry = require('web.kanban_examples_registry');

var _lt = core._lt;

var greenBullet = '<span class="o_status o_status_green"></span>';
var redBullet = '<span class="o_status o_status_red"></span>';
var star = '<a style="color: gold;" class="fa fa-star"/>';


/**
 * Helper function to escape a text before formatting it.
 *
 * First argument is the string to format and the other arguments are the values
 * to inject into the string.
 *
 * Sort of 'lazy escaping' as it is used alongside _lt.
 *
 * @returns {string} the formatted and escaped string
 */
function escFormat() {
    var args = arguments;
    return {
        toString: function () {
            args[0] = _.escape(args[0]);
            return _.str.sprintf.apply(_.str, args);
        },
    };
}

kanbanExamplesRegistry.add('project', [{
    name: _lt('Software Development'),
    columns: [_lt('Backlog'), _lt('Specifications'), _lt('Development'), _lt('Tests'), _lt('Delivered')],
    description: escFormat(_lt('Once a task is specified, set it %s in the Specifications ' +
        'column, so that developers know they can pull it. If you work in sprints, use %s to ' +
        'mark tasks of the current sprint.'), greenBullet, star),
}, {
    name: _lt('Agile'),
    columns: [_lt('Backlog'), _lt('Analysis'), _lt('Development'), _lt('Testing'), _lt('Done')],
    description: escFormat(_lt('Waiting for the next stage: use %s and %s bullets.'), greenBullet, redBullet),
}, {
    name: _lt('Digital Marketing'),
    columns: [_lt('Ideas'), _lt('Researching'), _lt('Writing'), _lt('Editing'), _lt('Done')],
    description: escFormat(_lt('Everyone can propose ideas, and the Editor marks the best ones ' +
        'as %s. Attach all documents or links to the task directly, to have all information about ' +
        'a research centralized.'), greenBullet),
}, {
    name: _lt('Customer Feedback'),
    columns: [_lt('New'), _lt('In development'), _lt('Done'), _lt('Refused')],
    description: escFormat(_lt('Customers propose feedbacks by email; Odoo creates tasks ' +
        'automatically, and you can communicate on the task directly. Your managers decide which ' +
        'feedback is accepted %s and which feedback is moved to the "Refused" column.'), greenBullet),
}, {
    name: _lt('Getting Things Done (GTD)'),
    columns: [_lt('Inbox'), _lt('Today'), _lt('This Week'), _lt('This Month'), _lt('Long Term')],
    description: _lt('Fill your Inbox easily with the email gateway. Periodically review your ' +
        'Inbox and schedule tasks by moving them to others columns. Every day, you review the ' +
        '"This Week" column to move important tasks "Today". Every Monday, you review the "This ' +
        'Month" column.'),
}, {
    name: _lt('Consulting'),
    columns: [_lt('New Projects'), _lt('Resources Allocation'), _lt('In Progress'), _lt('Done')],
}, {
    name: _lt('Research Project'),
    columns: [_lt('Brainstorm'), _lt('Research'), _lt('Draft'), _lt('Final Document')],
}, {
    name: _lt('Website Redesign'),
    columns: [_lt('Page Ideas'), _lt('Copywriting'), _lt('Design'), _lt('Live')],
}, {
    name: _lt('T-shirt Printing'),
    columns: [_lt('New Orders'), _lt('Logo Design'), _lt('To Print'), _lt('Done')],
    description: escFormat(_lt('Communicate with customers on the task using the email gateway. ' +
        'Attach logo designs to the task, so that information flow from designers to the workers ' +
        'who print the t-shirt. Organize priorities amongst orders %s using the icon.'), star),
}]);

});
