odoo.define('project.task_kanban_examples', function (require) {
'use strict';

var core = require('web.core');
var kanbanExamplesRegistry = require('web.kanban_examples_registry');

var _t = core._t;

var greenBullet = '<span class="o_status o_status_green"></span>';
var redBullet = '<span class="o_status o_status_red"></span>';
var star = '<a style="color: gold;" class="fa fa-star"/>';


/**
 * Helper function to escape a text before formatting it.
 *
 * First argument is the string to format and the other arguments are the values
 * to inject into the string.
 *
 * @returns {string} the formatted and escaped string
 */
function escFormat() {
    arguments[0] = _.escape(arguments[0]);
    return _.str.sprintf.apply(_.str, arguments);
}

kanbanExamplesRegistry.add('project', [{
    name: _t('Software Development'),
    columns: [_t('Backlog'), _t('Specifications'), _t('Development'), _t('Tests'), _t('Delivered')],
    description: escFormat(_t('Once a task is specified, set it %s in the Specifications ' +
        'column, so that developers know they can pull it. If you work in sprints, use %s to ' +
        'mark tasks of the current sprint.'), greenBullet, star),
}, {
    name: _t('Agile'),
    columns: [_t('Backlog'), _t('Analysis'), _t('Development'), _t('Testing'), _t('Done')],
    description: escFormat(_t('Waiting for the next stage: use %s and %s bullets.'), greenBullet, redBullet),
}, {
    name: _t('Digital Marketing'),
    columns: [_t('Ideas'), _t('Researching'), _t('Writing'), _t('Editing'), _t('Done')],
    description: escFormat(_t('Everyone can propose ideas, and the Editor marks the best ones ' +
        'as %s. Attach all documents or links to the task directly, to have all information about ' +
        'a research centralized.'), greenBullet),
}, {
    name: _t('Customer Feedback'),
    columns: [_t('New'), _t('In development'), _t('Done'), _t('Refused')],
    description: escFormat(_t('Customers propose feedbacks by email; Odoo creates tasks ' +
        'automatically, and you can communicate on the task directly. Your managers decide which ' +
        'feedback is accepted %s and which feedback is moved to the "Refused" column.'), greenBullet),
}, {
    name: _t('Getting Things Done (GTD)'),
    columns: [_t('Inbox'), _t('Today'), _t('This Week'), _t('This Month'), _t('Long Term')],
    description: _t('Fill your Inbox easily with the email gateway. Periodically review your ' +
        'Inbox and schedule tasks by moving them to others columns. Every day, you review the ' +
        '"This Week" column to move important tasks "Today". Every Monday, you review the "This ' +
        'Month" column.'),
}, {
    name: _t('Consulting'),
    columns: [_t('New Projects'), _t('Resources Allocation'), _t('In Progress'), _t('Done')],
}, {
    name: _t('Research Project'),
    columns: [_t('Brainstorm'), _t('Research'), _t('Draft'), _t('Final Document')],
}, {
    name: _t('Website Redesign'),
    columns: [_t('Page Ideas'), _t('Copywriting'), _t('Design'), _t('Live')],
}, {
    name: _t('T-shirt Printing'),
    columns: [_t('New Orders'), _t('Logo Design'), _t('To Print'), _t('Done')],
    description: escFormat(_t('Communicate with customers on the task using the email gateway. ' +
        'Attach logo designs to the task, so that information flow from designers to the workers ' +
        'who print the t-shirt. Organize priorities amongst orders %s using the icon.'), star),
}]);

});
