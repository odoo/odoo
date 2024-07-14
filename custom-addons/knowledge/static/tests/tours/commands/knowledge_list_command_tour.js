/** @odoo-module */

import { registry } from "@web/core/registry";
import { endKnowledgeTour, openCommandBar } from '../knowledge_tour_utils.js';
import { decodeDataBehaviorProps } from "@knowledge/js/knowledge_utils";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

const testName = "*()!'<>~";
let behaviorProps;

registry.category("web_tour.tours").add('knowledge_list_command_tour', {
    url: '/web',
    test: true,
    steps: () => [stepUtils.showAppsMenuItem(), { // open the Knowledge App
    trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
}, { // open the command bar
    trigger: '.odoo-editor-editable > p',
    run: function () {
        openCommandBar(this.$anchor[0]);
    },
}, { // click on the /list command
    trigger: '.oe-powerbox-commandName:contains("Item List")',
    run: 'click',
}, { // input a test name for the view
    trigger: '.modal-dialog #label',
    run: `text ${testName}`,
}, { // choose a name for the embedded view
    trigger: '.modal-footer button.btn-primary',
    run: 'click'
}, { // scroll to the embedded view to load it
    trigger: '.o_knowledge_behavior_type_embedded_view',
    run: function () {
        this.$anchor[0].scrollIntoView();
    },
}, { // wait for the list view to be mounted
    trigger: '.o_knowledge_behavior_type_embedded_view .o_list_renderer',
    run: () => {},
}, { // verify that the view has the correct name and store data-behavior-props
    trigger: '.o_knowledge_embedded_view .o_control_panel .o_breadcrumb .active:contains("*()!\'<>~")',
    run: () => {
        const embeddedViewElement = document.querySelector('.o_knowledge_behavior_type_embedded_view');
        behaviorProps = decodeDataBehaviorProps(embeddedViewElement.dataset.behaviorProps);
    }
}, { // click on rename button
    trigger: '.o_control_panel_breadcrumbs_actions .dropdown-toggle',
    run: 'click',
}, {
    trigger: '.dropdown-item:contains(Edit)'
}, { // click to validate the modal
    trigger: '.modal-footer button.btn-primary',
    run: 'click'
}, { // check that the name is the correct one and compare previous data-behavior-props and the new one (should be equivalent)
    trigger: '.o_knowledge_embedded_view .o_control_panel .o_breadcrumb .active:contains("*()!\'<>~")',
    run: () => {
        const embeddedViewElement = document.querySelector('.o_knowledge_behavior_type_embedded_view');
        const newBehaviorProps = decodeDataBehaviorProps(embeddedViewElement.dataset.behaviorProps);
        if (newBehaviorProps.display_name !== behaviorProps.display_name) {
            throw new Error('The name displayed should not have changed');
        }
        if (JSON.stringify(newBehaviorProps) !== JSON.stringify(behaviorProps)) {
            // check that knowledge.article render_embedded_view urllib.parse.quote did
            // produce an equivalent data-behavior-props as knowledge_utils encodeDataBehaviorProps encodeURIComponent
            throw new Error('data-behavior-props should be semantically the same as before');
        }
    }
}, { // click on rename button
    trigger: '.o_control_panel_breadcrumbs_actions .dropdown-toggle',
    run: 'click',
}, {
    trigger: '.dropdown-item:contains(Edit)'
}, { // rename the view
    trigger: '.modal-body input',
    run: 'text New Title',
}, { // click to validate the modal
    trigger: '.modal-footer button.btn-primary',
    run: 'click',
}, { // check that name has been updated
    trigger: '.o_knowledge_embedded_view .o_control_panel .o_breadcrumb .active:contains("New Title")',
    run: () => {},
}, {
    // reload the article to make sure that the article is saved for readonly tour
    trigger: 'a[data-menu-xmlid="knowledge.knowledge_menu_home"]',
}, { // wait for embed to be visible
    trigger: '.o_knowledge_behavior_type_embedded_view',
}, ...endKnowledgeTour()
]});
