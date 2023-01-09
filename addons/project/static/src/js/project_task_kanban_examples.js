/** @odoo-module **/

import { _lt } from 'web.core';
import kanbanExamplesRegistry from 'web.kanban_examples_registry';
import { registry } from "@web/core/registry";
import { renderToMarkup } from '@web/core/utils/render';

const { markup } = owl;
const greenBullet = markup(`<span class="o_status d-inline-block o_status_green"></span>`);
const redBullet = markup(`<span class="o_status d-inline-block o_status_red"></span>`);
const star = markup(`<a style="color: gold;" class="fa fa-star"></a>`);
const clock = markup(`<a class="fa fa-clock-o"></a>`);

const exampleData = {
    ghostColumns: [_lt('New'), _lt('Assigned'), _lt('In Progress'), _lt('Done')],
    applyExamplesText: _lt("Use This For My Project"),
    examples:[{
        name: _lt('Software Development'),
        columns: [_lt('Backlog'), _lt('Specifications'), _lt('Development'), _lt('Tests'), _lt('Delivered')],
        get description() {
            return renderToMarkup("project.example.generic");
        },
        bullets: [greenBullet, redBullet, star],
    }, {
        name: _lt('Agile Scrum'),
        columns: [_lt('Backlog'), _lt('Sprint Backlog'), _lt('Sprint in Progress'), _lt('Sprint Complete'), _lt('Old Completed Sprint')],
        get description() {
            return renderToMarkup("project.example.agilescrum");
        },
        bullets: [greenBullet, redBullet],
    }, {
        name: _lt('Digital Marketing'),
        columns: [_lt('Ideas'), _lt('Researching'), _lt('Writing'), _lt('Editing'), _lt('Done')],
        get description() {
            return renderToMarkup("project.example.digitalmarketing");
        },
        bullets: [greenBullet, redBullet],
    }, {
        name: _lt('Customer Feedback'),
        columns: [_lt('New'), _lt('In development'), _lt('Done'), _lt('Refused')],
        get description() {
            return renderToMarkup("project.example.customerfeedback");
        },
        bullets: [greenBullet, redBullet],
    }, {
        name: _lt('Consulting'),
        columns: [_lt('New Projects'), _lt('Resources Allocation'), _lt('In Progress'), _lt('Done')],
        get description() {
            return renderToMarkup("project.example.consulting");
        },
        bullets: [greenBullet, redBullet],
    }, {
        name: _lt('Research Project'),
        columns: [_lt('Brainstorm'), _lt('Research'), _lt('Draft'), _lt('Final Document')],
        get description() {
            return renderToMarkup("project.example.researchproject");
        },
        bullets: [greenBullet, redBullet],
    }, {
        name: _lt('Website Redesign'),
        columns: [_lt('Page Ideas'), _lt('Copywriting'), _lt('Design'), _lt('Live')],
        get description() {
            return renderToMarkup("project.example.researchproject");
        },
    }, {
        name: _lt('T-shirt Printing'),
        columns: [_lt('New Orders'), _lt('Logo Design'), _lt('To Print'), _lt('Done')],
        get description() {
            return renderToMarkup("project.example.tshirtprinting");
        },
        bullets: [star],
    }, {
        name: _lt('Design'),
        columns: [_lt('New Request'), _lt('Design'), _lt('Client Review'), _lt('Handoff')],
        get description() {
            return renderToMarkup("project.example.generic");
        },
        bullets: [greenBullet, redBullet, star, clock],
    }, {
        name: _lt('Publishing'),
        columns: [_lt('Ideas'), _lt('Writing'), _lt('Editing'), _lt('Published')],
        get description() {
            return renderToMarkup("project.example.generic");
        },
        bullets: [greenBullet, redBullet, star, clock],
    }, {
        name: _lt('Manufacturing'),
        columns: [_lt('New Orders'), _lt('Material Sourcing'), _lt('Manufacturing'), _lt('Assembling'), _lt('Delivered')],
        get description() {
            return renderToMarkup("project.example.generic");
        },
        bullets: [greenBullet, redBullet, star, clock],
    }, {
        name: _lt('Podcast and Video Production'),
        columns: [_lt('Research'), _lt('Script'), _lt('Recording'), _lt('Mixing'), _lt('Published')],
        get description() {
            return renderToMarkup("project.example.generic");
        },
        bullets: [greenBullet, redBullet, star, clock],
    }],
};

kanbanExamplesRegistry.add('project', exampleData);
registry.category("kanban_examples").add('project', exampleData);
