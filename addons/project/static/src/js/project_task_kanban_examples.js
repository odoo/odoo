/** @odoo-module **/

import { _lt } from 'web.core';
import {Markup} from 'web.utils';
import kanbanExamplesRegistry from 'web.kanban_examples_registry';
import { registry } from "@web/core/registry";

const greenBullet = Markup`<span class="o_status d-inline-block o_status_green"></span>`;
const redBullet = Markup`<span class="o_status d-inline-block o_status_red"></span>`;
const star = Markup`<a style="color: gold;" class="fa fa-star"/>`;
const clock = Markup`<a class="fa fa-clock-o"/>`;

const _Markup = owl.markup('').constructor.prototype;
const descriptionActivities = escFormat(_lt('%s Use the %s icon to organize your daily activities.'), '<br/>', clock);
const description = escFormat(_lt('Prioritize Tasks by using the %s icon.' +
            '%s Use the %s button to signalize to your colleagues that a task is ready for the next stage.' +
            '%s Use the %s to signalize a problem or a need for discussion on a task.' +
            '%s'), star, '<br/>', greenBullet, '<br/>', redBullet, descriptionActivities);

/**
 * Helper function to escape the format string, but not the values formatted in,
 * rougly equivalent to `_.str.sprintf(_.escape(fmt), ...)`.
 *
 * Performs the escaping lazily (at point of use) as it's designed to be used
 * with `_lt` as the source of the format string.
 *
 * @param fmt format string, to escape
 * @param args objects to format into `fmt`, unescaped
 * @returns {Object} a stringifiable object returning the escaped then formatted string
 */
function escFormat(fmt, ...args) {
    // Returned object needs to be instanceof owl Markup so that owl will insert it correctly
    return Object.create(
        _Markup,
        Object.getOwnPropertyDescriptors({
            [_.escapeMethod]() {
                return this;
            },
            toString() {
                return _.str.sprintf(_.escape(fmt), ...args);
            },
        })
    );
}

const exampleData = {
    ghostColumns: [_lt('New'), _lt('Assigned'), _lt('In Progress'), _lt('Done')],
    applyExamplesText: _lt("Use This For My Project"),
    examples:[{
        name: _lt('Software Development'),
        columns: [_lt('Backlog'), _lt('Specifications'), _lt('Development'), _lt('Tests'), _lt('Delivered')],
        description: escFormat(_lt('Prioritize Tasks by using the %s icon.' +
            '%s Use the %s button to inform your colleagues that a task is ready for the next stage.' +
            '%s Use the %s to indicate a problem or a need for discussion on a task.' +
            '%s'), star, '<br/>', greenBullet, '<br/>', redBullet, descriptionActivities),
        bullets: [greenBullet, redBullet, star],
    }, {
        name: _lt('Agile Scrum'),
        columns: [_lt('Backlog'), _lt('Sprint Backlog'), _lt('Sprint in Progress'), _lt('Sprint Complete'), _lt('Old Completed Sprint')],
        description: escFormat(_lt('Use %s and %s bullets to indicate the status of a task. %s'), greenBullet, redBullet, descriptionActivities),
        bullets: [greenBullet, redBullet],
    }, {
        name: _lt('Digital Marketing'),
        columns: [_lt('Ideas'), _lt('Researching'), _lt('Writing'), _lt('Editing'), _lt('Done')],
        description: escFormat(_lt('Everyone can propose ideas, and the Editor marks the best ones ' +
            'as %s. Attach all documents or links to the task directly, to have all research information centralized. %s'), greenBullet, descriptionActivities),
        bullets: [greenBullet, redBullet],
    }, {
        name: _lt('Customer Feedback'),
        columns: [_lt('New'), _lt('In development'), _lt('Done'), _lt('Refused')],
        description: escFormat(_lt('Customers propose feedbacks by email; Odoo creates tasks ' +
            'automatically, and you can communicate on the task directly. Your managers decide which ' +
            'feedback is accepted %s and which feedback is moved to the %s column. %s'), greenBullet, _lt('"Refused"'), descriptionActivities),
        bullets: [greenBullet, redBullet],
    }, {
        name: _lt('Consulting'),
        columns: [_lt('New Projects'), _lt('Resources Allocation'), _lt('In Progress'), _lt('Done')],
        description: escFormat(_lt('Manage the lifecycle of your project using the kanban view. Add newly acquired projects, assign them and use the %s and %s to define if the project is ready for the next step. %s'), greenBullet, redBullet, descriptionActivities),
        bullets: [greenBullet, redBullet],
    }, {
        name: _lt('Research Project'),
        columns: [_lt('Brainstorm'), _lt('Research'), _lt('Draft'), _lt('Final Document')],
        description: escFormat(_lt('Handle your idea gathering within Tasks of your new Project and discuss them in the chatter of the tasks. Use the %s and %s to signalize what is the current status of your Idea. %s'), greenBullet, redBullet, descriptionActivities),
        bullets: [greenBullet, redBullet],
    }, {
        name: _lt('Website Redesign'),
        columns: [_lt('Page Ideas'), _lt('Copywriting'), _lt('Design'), _lt('Live')],
        description: escFormat(_lt('Handle your idea gathering within Tasks of your new Project and discuss them in the chatter of the tasks. Use the %s and %s to signalize what is the current status of your Idea. %s'), greenBullet, redBullet, descriptionActivities),
    }, {
        name: _lt('T-shirt Printing'),
        columns: [_lt('New Orders'), _lt('Logo Design'), _lt('To Print'), _lt('Done')],
        description: escFormat(_lt('Communicate with customers on the task using the email gateway. ' +
            'Attach logo designs to the task, so that information flows from designers to the workers ' +
            'who print the t-shirt. Organize priorities amongst orders using the %s icon. %s'), star, descriptionActivities),
        bullets: [star],
    }, {
        name: _lt('Design'),
        columns: [_lt('New Request'), _lt('Design'), _lt('Client Review'), _lt('Handoff')],
        description: description,
        bullets: [greenBullet, redBullet, star, clock],
    }, {
        name: _lt('Publishing'),
        columns: [_lt('Ideas'), _lt('Writing'), _lt('Editing'), _lt('Published')],
        description: description,
        bullets: [greenBullet, redBullet, star, clock],
    }, {
        name: _lt('Manufacturing'),
        columns: [_lt('New Orders'), _lt('Material Sourcing'), _lt('Manufacturing'), _lt('Assembling'), _lt('Delivered')],
        description: description,
        bullets: [greenBullet, redBullet, star, clock],
    }, {
        name: _lt('Podcast and Video Production'),
        columns: [_lt('Research'), _lt('Script'), _lt('Recording'), _lt('Mixing'), _lt('Published')],
        description: description,
        bullets: [greenBullet, redBullet, star, clock],
    }],
};

kanbanExamplesRegistry.add('project', exampleData);
registry.category("kanban_examples").add('project', exampleData);
