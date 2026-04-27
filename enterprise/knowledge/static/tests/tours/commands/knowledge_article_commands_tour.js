/** @odoo-module */

import { Component, markup, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

import {
    appendArticleLink,
    embeddedViewPatchFunctions,
    endKnowledgeTour,
    openPowerbox,
} from "../knowledge_tour_utils.js";
import { EmbeddedVideoComponent } from "@html_editor/others/embedded_components/core/video/video";

import { VideoSelector } from "@html_editor/main/media/media_dialog/video_selector";
import { HtmlField } from "@html_editor/fields/html_field";
import { Editor } from "@html_editor/editor";

/**
 * This is a global knowledge tour testing commands and their usage.
 *
 * If you need to edit this tour, here are a few recommendations:
 * - Try to keep the steps light and test specifically your command
 * - Keep the commands modifying the main article at the top
 * - Ideally, those commands should NOT leave this article, and just modify its content
 * - Embed view commands are grouped together right after the other commands
 * - If you need to test something that leaves the article to test your command usage
 *   (go into another menu, switch article, ...), it's better to put it after everything else,
 *   in the "MISC" section.
 *   Indeed, trying to input commands when rapidly switching from another view / article can create
 *   some race conditions with the editor, leading to hard-to-debug issues
 *   (e.g: "Component is destroyed").
 */

//------------------------------------------------------------------------------
// UTILS
//------------------------------------------------------------------------------

const embeddedViewPatchUtil = embeddedViewPatchFunctions();

const embedViewSelector = (embedViewName) => {
    return `[data-embedded="view"]:has( .o_last_breadcrumb_item:contains("${embedViewName}"))`;
};

const commonKanbanSteps = (embedViewName) => {
    return [
        { // scroll to the embedded view to load it
            trigger: embedViewSelector(embedViewName),
            run: function () {
                this.anchor.scrollIntoView();
            },
        }, { // wait for the kanban view to be mounted
            trigger: `${embedViewSelector(embedViewName)} .o_kanban_renderer`,
        },
    ];
};

let articleId;
let plugin;
const unpatchHtmlField = patch(HtmlField.prototype, {
    setup() {
        super.setup();
        articleId = this.props.record.resId;
    },
});

const unpatchEditor = patch(Editor.prototype, {
    preparePlugins() {
        super.preparePlugins();
        plugin = this.plugins.find((p) => p.insertEmbeddedView);
    },
});

//------------------------------------------------------------------------------
// TOUR STEPS - KNOWLEDGE COMMANDS
//------------------------------------------------------------------------------

// COMMAND: /article

// WARNING: uses the legacy editor powerbox.
const articleCommandSteps = [
    { // open the command bar
        trigger: `[name="body"] .odoo-editor-editable > p:last-child`,
        run: function () {
            openPowerbox(this.anchor);
        },
    }, { // click on the /article command
        trigger: '.o-we-powerbox .o-we-command-name:contains(Article)',
        run: 'click',
    }, {
        // select an article in the list
        // 'not has span' is used to remove children articles as they also contain the article name
        trigger: `.o_select_menu_item > span:not(:has(span)):contains(LinkedArticle)`,
        run: 'click',
    }, { // wait for the choice to be registered
        trigger: `.o_select_menu_toggler_slot:contains(LinkedArticle)`,
    }, { // click on the "Insert Link" button
        trigger: '.modal-dialog:contains(Link an Article) .modal-footer button.btn-primary',
        run: 'click'
    }
];

// COMMAND: /file

const fileCommandSteps = [{ // open the command bar
    trigger: '.odoo-editor-editable > p',
    run: function () {
        openPowerbox(this.anchor);
    },
}, { // click on the /media command
    trigger: '.o-we-command-name:contains("Media")',
    run: 'click',
}, { // Pick  the "Documents" tab
    trigger: '.o_select_media_dialog .nav-tabs .nav-link:contains("Documents")',
    run: 'click',
}, { // click on the first item of the modal
    trigger: '.o_existing_attachment_cell:contains(Onboarding)',
    run: 'click'
}, { // wait for the block to appear in the editor
    trigger: "[data-embedded='file'] span.o_file_image a",
    run: 'click',
},
{
    trigger: '.o-FileViewer-view:iframe body:contains(Content)',
},
{
    trigger: '.o-FileViewer-headerButton[aria-label="Close"]',
    run: 'click',
}, {
    trigger: ".o_file_name_container:contains(Onboarding)",
    run: function() {
        this.anchor.dispatchEvent(new Event("focus"));
    }
}, {
    trigger: ".o_file_name_container + input",
    run: function() {
        this.anchor.value = "Renamed";
        this.anchor.dispatchEvent(new Event("blur"));
    },
}, {
    trigger: "span.o_file_name",
    run: function () {
        // specifically test that there is no zeroWidthSpace character in the
        // name that would be added by the editor
        const currentName = this.anchor.textContent;
        if (currentName !== "Renamed") {
            throw new Error(`The new file name was expected to be: "Renamed", but the actual value is: "${currentName}"`);
        }
    }
}];

// COMMAND: /index

const indexCommandSteps = [{ // open the command bar
    trigger: '.odoo-editor-editable > p',
    run: function () {
        openPowerbox(this.anchor);
    },
}, { // click on the /index command
    trigger: '.o-we-command-name:contains("Index")',
    run: 'click',
}, { // wait for the block to appear in the editor
    trigger: '[data-embedded="articleIndex"]',
}, { // click on the refresh button
    trigger: '[data-embedded="articleIndex"] button[title="Update"]',
    run: 'click',
}, { // click on the switch mode button
    trigger: '[data-embedded="articleIndex"] button[title="Switch Mode"]',
    run: 'click',
}];

// COMMAND: /toc (table of contents)

const tocCommandSteps = [{ // open the command bar
    trigger: '.odoo-editor-editable > p',
    run: function () {
        openPowerbox(this.anchor);
    },
}, { // click on the /toc command
    trigger: '.o-we-command-name:contains("Table Of Content")',
    run: 'click',
}, { // wait for the block to appear in the editor
    trigger: '[data-embedded="tableOfContent"]',
}, { // insert a few titles in the editor
    trigger: '.odoo-editor-editable > p',
    run: function () {
        const toCreate = [
            ["h1", "Title 1"],
            ["h2", "Title 1.1"],
            ["h3", "Title 1.1.1"],
            ["h2", "Title 1.2"],
        ];
        toCreate.forEach((el) => {
            const elem = document.createElement(el[0]);
            elem.textContent = el[1];
            this.anchor.appendChild(elem);
        })
        this.anchor.dispatchEvent(new Event("input", { bubbles: true }));
    },
}, { // click on the h1 anchor link generated by the toc
    trigger: '.o_embedded_toc_link_depth_0',
    run: 'click',
}, { // open the tools panel
    trigger: '#dropdown_tools_panel',
    run: 'click',
}, { // switch to locked (readonly) mode
    trigger: '.o_knowledge_more_options_panel .btn-lock',
    run: 'click',
}, { // check that we are in readonly mode
    trigger: '.o_field_html .o_readonly',
}, { // check that the content of the toc is not duplicated
    trigger: '[data-embedded="tableOfContent"]',
    run: function () {
        if (this.anchor.querySelectorAll(".o_embedded_toc_content").length !== 1) {
            throw new Error('The table of content group of links should be present exactly once (not duplicated)');
        }
    },
}, { // click on the h1 anchor link generated by the toc
    trigger: '.o_embedded_toc_link_depth_0',
    run: 'click',
}, { // open the tools panel
    trigger: '#dropdown_tools_panel',
    run: 'click',
}, { // unlock the article
    trigger: '.o_knowledge_more_options_panel.show .btn-lock',
    run: 'click',
}, { // check that we are in edit mode
    trigger: '.o_field_html .odoo-editor-editable',
}];

// COMMAND: /clipboard

const clipboardCommandSteps = [{ // go to the custom article
    trigger: '.o_article .o_article_name:contains("EditorCommandsArticle")',
    run: "click",
}, { // wait for article to be correctly loaded
    trigger: '.o_hierarchy_article_name input:value("EditorCommandsArticle")',
}, { // open the command bar
    trigger: '.odoo-editor-editable > p',
    run: function () {
        openPowerbox(this.anchor);
    },
}, { // click on the /clipboard command
    trigger: '.o-we-command-name:contains("Clipboard")',
    run: 'click',
}, { // wait for the block to appear in the editor
    trigger: "[data-embedded='clipboard']",
}, { // enter text into the clipboard template
    trigger: "[data-embedded-editable='clipboardContent'] > p",
    run: "editor Hello world",
}, { // verify that the text was correctly inserted
    trigger: "[data-embedded-editable='clipboardContent'] > p:contains(Hello world)",
}];

// COMMAND: /video

const YoutubeVideoId = "Rk1MYMPDx3s";
let unpatchVideoEmbed;
let unpatchVideoSelector;

class MockedVideoIframe extends Component {
    static template = xml`
        <div class="o_video_iframe_src" t-out="props.src" />
    `;
    static props = ["src"];
}

const videoCommandSteps = [{ // patch the components
    trigger: "body",
    run: () => {
        unpatchVideoEmbed = patch(EmbeddedVideoComponent.components, {
            ...EmbeddedVideoComponent.components,
            VideoIframe: MockedVideoIframe
        });
        unpatchVideoSelector = patch(VideoSelector.components, {
            ...VideoSelector.components,
            VideoIframe: MockedVideoIframe
        });
    },
}, { // open the command bar
    trigger: ".odoo-editor-editable > p",
    run: function () {
        openPowerbox(this.anchor);
    },
}, { // click on the /video command
    trigger: '.o-we-command-name:contains("Video")',
    run: "click",
}, {
    content: "Enter a video URL",
    trigger: ".modal-body #o_video_text",
    run: `edit https://www.youtube.com/watch?v=${YoutubeVideoId}`,
}, {
    content: "Wait for preview to appear",
    trigger: `.o_video_iframe_src:contains("//www.youtube.com/embed/${YoutubeVideoId}?rel=0&autoplay=0")`,
}, {
    content: "Confirm selection",
    trigger: '.modal-footer button:contains("Insert Video")',
    run: "click",
},
{
    trigger: `[data-embedded="video"] .o_video_iframe_src:contains("https://www.youtube.com/embed/${YoutubeVideoId}?rel=0&autoplay=0")`,
},
{ // wait for the block to appear in the editor
    trigger: '[data-embedded="video"]',
    run: function () {
        // ensure that the video element is not in the DOM, to avoid
        // rendering it in the readonly tour.
        this.anchor.remove();
    },
}];

const unpatchSteps = [{ // unpatch the components
    trigger: "body",
    run: () => {
        unpatchVideoEmbed();
        unpatchVideoSelector();
        embeddedViewPatchUtil.after();
        unpatchHtmlField();
        unpatchEditor();
    },
}];

//------------------------------------------------------------------------------
// TOUR STEPS - KNOWLEDGE EMBED VIEWS
//------------------------------------------------------------------------------

const embeddedViewPatchSteps = [{
    trigger: 'body',
    run: embeddedViewPatchUtil.before,
}];

// EMBED VIEW: /list

let embeddedProps;
const embedListName = "List special chars *()!'<>~";
const listCommandSteps = [{ // open the command bar
    trigger: '.odoo-editor-editable > p',
    run: function () {
        openPowerbox(this.anchor);
    },
}, { // click on the /list command
    trigger: '.o-we-command-name:contains("Item List")',
    run: 'click',
}, { // input a test name for the view
    trigger: '.modal-dialog #label',
    run: `edit ${embedListName}`,
}, { // choose a name for the embedded view
    trigger: '.modal-footer button.btn-primary',
    run: 'click'
}, { // scroll to the embedded view to load it
    trigger: embedViewSelector(embedListName),
    run: function () {
        this.anchor.scrollIntoView();
    },
}, { // wait for the list view to be mounted
    trigger: `${embedViewSelector(embedListName)} .o_list_renderer`,
}, { // verify that the view has the correct name and store data-embedded-props
    trigger: `${embedViewSelector(embedListName)} .o_control_panel .o_breadcrumb .active:contains("*()!'<>~")`,
    run: () => {
        const embeddedViewElement = document.querySelector('[data-embedded="view"]');
        embeddedProps = JSON.parse(embeddedViewElement.dataset.embeddedProps);
    }
}, { // click on rename button
    trigger: '.o_control_panel_breadcrumbs_actions .dropdown-toggle',
    run: 'click',
}, {
    trigger: '.dropdown-item:contains(Edit)',
    run: "click",
}, { // click to validate the modal
    trigger: '.modal-footer button.btn-primary',
    run: 'click'
}, { // check that the name is the correct one and compare previous data-embedded-props and the new one (should be equivalent)
    trigger: `${embedViewSelector(embedListName)} .o_control_panel .o_breadcrumb .active:contains("*()!'<>~")`,
    run: () => {
        const embeddedViewElement = document.querySelector('[data-embedded="view"]');
        const newEmbeddedProps = JSON.parse(embeddedViewElement.dataset.embeddedProps);
        if (newEmbeddedProps.display_name !== embeddedProps.display_name) {
            throw new Error('The name displayed should not have changed');
        }
        if (JSON.stringify(newEmbeddedProps) !== JSON.stringify(embeddedProps)) {
            // check that knowledge.article render_embedded_view urllib.parse.quote did
            // produce an equivalent data-embedded-props as
            throw new Error('data-embedded-props should be semantically the same as before');
        }
    }
}, { // click on rename button
    trigger: '.o_control_panel_breadcrumbs_actions .dropdown-toggle',
    run: 'click',
}, {
    trigger: '.dropdown-item:contains(Edit)',
    run: "click",
}, { // rename the view
    trigger: '.modal-body input',
    run: "edit New Title",
}, { // click to validate the modal
    trigger: '.modal-footer button.btn-primary',
    run: 'click',
}, { // check that name has been updated
    trigger: '[data-embedded="view"] .o_control_panel .o_breadcrumb .active:contains("New Title")',
}];

// EMBED VIEW: /kanban

const embedKanbanName = "My Tasks Kanban";
const embedKanbanSteps = [{ // open the command bar
    trigger: '.odoo-editor-editable > p',
    run: function () {
        openPowerbox(this.anchor);
    },
}, { // click on the /kanban command
    trigger: '.o-we-command-name:contains("Item Kanban")',
    run: 'click',
}, { // input a test name for the view
    trigger: '.modal-dialog #label',
    run: `edit ${embedKanbanName}`,
}, { // choose a name for the embedded view
    trigger: `.modal-dialog:contains("Insert a Kanban View") .modal-footer button.btn-primary`,
    run: 'click',
},
...commonKanbanSteps(embedKanbanName),
{ // Check that the stages are well created
    trigger: `${embedViewSelector(embedKanbanName)} .o_kanban_renderer .o_kanban_group .o_kanban_header_title:contains("Ongoing")`,
}, { // create an article item from Main New button
    trigger: `${embedViewSelector(embedKanbanName)} .o-kanban-button-new`,
    run: 'click',
}, { // Type a Title for new article in the quick create form
    trigger: `${embedViewSelector(embedKanbanName)} .o_kanban_renderer .o_kanban_quick_create .o_input`,
    run: "edit New Quick Create Item",
}, { // Add a random icon to the new article in the quick create form
    trigger: `${embedViewSelector(embedKanbanName)} .o_kanban_renderer .o_kanban_quick_create a[title="Add a random icon"]`,
    run: 'click',
}, { // Click on the icon to open the emoji picker and select another icon in the quick create form
    trigger: `${embedViewSelector(embedKanbanName)} .o_kanban_renderer .o_kanban_quick_create .o_article_emoji`,
    run: 'click',
}, { // Select an emoji for the new article
    trigger: '.o-Emoji[data-codepoints="🙃"]',
    run: 'click',
}, { // Click on Add to create the article
    trigger: `${embedViewSelector(embedKanbanName)} .o_kanban_renderer .o_kanban_quick_create .o_kanban_add`,
    run: 'click'
},
{
    trigger: `${embedViewSelector(embedKanbanName)} .o_kanban_renderer .o_article_emoji:contains("🙃")`,
},
{ // Verify that the article has been properly created
    trigger: `${embedViewSelector(embedKanbanName)} .o_kanban_renderer span:contains("New Quick Create Item")`,
}, { // Click on the icon of the created article to open the emoji picker
    trigger: `${embedViewSelector(embedKanbanName)} .o_kanban_renderer .o_article_emoji`,
    run: 'click',
}, { // Select another emoji for the created article
    trigger: '.o-Emoji[data-codepoints="🤩"]',
    run: 'click',
}];

// EMBED VIEW: /cards (same as kanban, without the custom stages)

const embedCardsKanbanName = "My Cards Kanban";
const embedCardsKanbanSteps = [{ // open the command bar
    trigger: '.odoo-editor-editable > p',
    run: function () {
        openPowerbox(this.anchor);
    },
}, { // click on the /kanban command
    trigger: '.o-we-command-name:contains("Item Cards")',
    run: 'click',
}, { // input a test name for the view
    trigger: '.modal-dialog #label',
    run: `edit ${embedCardsKanbanName}`,
}, { // choose a name for the embedded view
    trigger: `.modal-dialog:contains("Insert a Kanban View") .modal-footer button.btn-primary`,
    run: 'click',
},
...commonKanbanSteps(embedCardsKanbanName)];

/*
 * EMBED VIEW: /kanban - with custom act_window
 * Allows testing that we support a fully custom act.window definition to create embed views.
 */

const embedKanbanActWindowName = "Act Window Kanban";
const articleItemsKanbanAction = {
    domain: "[('parent_id', '=', active_id), ('is_article_item', '=', True)]",
    help: markup('<p class="o_nocontent_help">No data to display</p>'),
    name: embedKanbanActWindowName,
    res_model: 'knowledge.article',
    type: 'ir.actions.act_window',
    views: [[false, 'kanban']],
    view_mode: 'kanban',
};

const articleItemsKanbanActionContext = () => {
    return {
        active_id: articleId,
        default_parent_id: articleId,
        default_is_article_item: true,
    };
};

const embedKanbanActWindowSteps = [{ // manually insert view from act_window object
    trigger: '.odoo-editor-editable > p',
    run: function () {
        const context = articleItemsKanbanActionContext();
        const selection = document.getSelection();
        selection.setBaseAndExtent(this.anchor, 0, this.anchor, 0);
        plugin.insertEmbeddedView(
            articleItemsKanbanAction,
            articleItemsKanbanAction.name,
            "kanban",
            { context }
        );
    },
},
...commonKanbanSteps(embedKanbanActWindowName)];

//------------------------------------------------------------------------------
// TOUR STEPS - MISC
//------------------------------------------------------------------------------

/*
 * MISC: Verifying view filtering mechanics.
 * When you enable a filter on an embed view, it it saved and restored if you go back to that view.
 * See: 'knowledgeEmbedViewsFilters' for more details
 */

const embedViewFiltersSteps = [{
    // Check that we have 2 elements in the embedded view
    trigger: 'tbody tr.o_data_row:nth-child(2)',
}, { // add a simple filter
    trigger: '.o_searchview_input_container input',
    run: "edit 1",
}, {
    trigger: 'li[id="1"]',
    run: "click",
}, { // Check that the filter is effective
    trigger: 'tbody:not(tr.o_data_row:nth-child(2))',
}, { // Open the filtered article
    trigger: 'tbody > tr > td[name="display_name"]',
    run: "click",
}, { // Wait for the article to be open
    trigger: '.o_hierarchy_article_name input:value("Child 1")',
}, { // Go back via the pager
    trigger: '.o_knowledge_header i.oi-chevron-left',
    run: "click",
}, { // Check that there is the filter in the searchBar
    trigger: '.o_searchview_input_container',
}, { // Check that the filter is effective
    trigger: 'tbody:not(tr.o_data_row:nth-child(2))',
}];

// MISC: Test opening an article item through the kanban view

const embedKanbanEditArticleSteps = [{ // Create a new article using quick create in OnGoing Column
    trigger: `${embedViewSelector(embedKanbanName)} .o_kanban_renderer .o_kanban_group .o_kanban_header_title:contains("Ongoing") .o_kanban_quick_add`,
    run: 'click'
}, { // Type a Title for new article in the quick create form
    trigger: `${embedViewSelector(embedKanbanName)} .o_kanban_renderer .o_kanban_group:has(.o_kanban_header_title:contains("Ongoing")) .o_kanban_quick_create .o_input`,
    run: "edit Quick Create Ongoing Item",
}, { // Click on Edit to open the article in edition in his own form view
    trigger: `${embedViewSelector(embedKanbanName)} .o_kanban_renderer .o_kanban_quick_create .o_kanban_edit`,
    run: 'click'
}, { // verify that the view switched to the article item
    trigger: '.o_knowledge_header .o_hierarchy_article_name input:value("Quick Create Ongoing Item")',
}, { // Go back via the pager
    trigger: '.o_knowledge_header i.oi-chevron-left',
    run: "click",
}, { // Wait for the article to be properly loaded
    trigger: '.odoo-editor-editable:contains("EditorCommandsArticle Content")',
}];

/*
 * MISC: Verifying /article command inside the mail composer.
 * We add specific code to make the /article command work inside the composer, notably in relation
 * to the "to inline" process.
 * See '_toInline' knowledge override in html_field.js
 */

const composeBody = ".modal-dialog:contains(Compose Email) [name='body']";
const articleCommandComposerSteps = [{ // open the chatter
    trigger: '.btn-chatter',
    run: "click",
}, { // open the message editor
    trigger: '.o-mail-Chatter-sendMessage:not([disabled=""])',
    run: "click",
}, { // open the full composer
    trigger: "button[aria-label='Full composer']",
    run: "click",
}, {
    trigger: `${composeBody} .odoo-editor-editable > div.o-paragraph`,
}, ...appendArticleLink(`${composeBody}`, 'EditorCommandsArticle'), { // wait for the block to appear in the editor
    trigger: `${composeBody} .o_knowledge_article_link:contains("EditorCommandsArticle")`,
}, ...appendArticleLink(`${composeBody}`, 'LinkedArticle', `.o_knowledge_article_link:contains("EditorCommandsArticle")`), { // wait for the block to appear in the editor, after the previous one
    trigger: `${composeBody} .odoo-editor-editable a:nth-child(2).o_knowledge_article_link:contains("LinkedArticle")[contenteditable="false"]`,
}, { // verify that the first block is still there and contenteditable=false
    trigger: `${composeBody} .odoo-editor-editable a:nth-child(1).o_knowledge_article_link:contains("EditorCommandsArticle")[contenteditable="false"]`,
}, { // send the message
    trigger: '.o_mail_send',
    run: "click",
}, {
    trigger: '.o_widget_knowledge_chatter_panel .o-mail-Thread .o-mail-Message-body a:nth-child(1).o_knowledge_article_link:contains("EditorCommandsArticle")',
}, {
    trigger: '.o_widget_knowledge_chatter_panel .o-mail-Thread .o-mail-Message-body a:nth-child(2).o_knowledge_article_link:contains("LinkedArticle")',
}, { // close the chatter
    trigger: '.btn-chatter',
    run: 'click',
}];

// MISC: Article command usage

const articleCommandUsageSteps = [{ // wait for the block to appear in the editor
    trigger: '.o_knowledge_article_link:contains("LinkedArticle")',
    run: 'click',
}, { // check that the view switched to the corresponding article
    trigger: '.o_knowledge_header:has(.o_hierarchy_article_name input:value("LinkedArticle"))',
    run: "click",
}, { // Go back via the pager
    trigger: '.o_knowledge_header i.oi-chevron-left',
    run: "click",
}, { // Wait for the article to be properly loaded
    trigger: '.odoo-editor-editable:contains("EditorCommandsArticle Content")',
}];

/** MISC: Clipboard usage on a contact
 *
 * Has to stay last for 2 reasons:
 * - It's important to be executed in an article that has embed views inside it, to make sure that
 *   the breadcrumbs from embed views don't interfere with the macro system ;
 * - It actually leaves the main article, meaning any steps after this one would have to manually
 *   re-enter the article from the Knowledge app (could have side effects, see file introduction).
 */

const clipboardUsageSteps = [{ // open the chatter
    trigger: '.btn-chatter',
    run: 'click',
}, {
    trigger: '.o-mail-Thread',
}, { // open the follower list of the article
    trigger: '.o-mail-Followers-button',
    run: 'click',
}, { // open the contact record of the follower
    trigger: '.o-mail-Follower-details:contains(HelloWorldPartner)',
    run: 'click',
}, { // verify that the partner form view is fully loaded
    trigger: '.o_breadcrumb .o_last_breadcrumb_item.active:contains(HelloWorldPartner)',
}, { // return to the knowledge article by going back from the breadcrumbs
    trigger: '.o_breadcrumb a:contains(EditorCommandsArticle)',
    run: 'click',
}, {
    trigger: "[data-embedded='clipboard'] button:first:contains(Copy)",
}, { // open the chatter again
    trigger: '.btn-chatter',
    run: 'click',
}, {
    trigger: '.o-mail-Thread',
}, { // open the follower list of the article
    trigger: '.o-mail-Followers-button',
    run: 'click',
}, { // open the contact record of the follower
    trigger: '.o-mail-Follower-details:contains(HelloWorldPartner)',
    run: 'click',
}, { // verify that the partner form view is fully loaded
    trigger: '.o_breadcrumb .o_last_breadcrumb_item.active:contains(HelloWorldPartner)',
}, { // search an article to open it from the contact record
    trigger: 'button[title="Search Knowledge Articles"]',
    run: 'click',
}, { // open the article
    trigger: '.o_command_default:contains(EditorCommandsArticle)',
    run: 'click',
}, { // wait for article to be correctly loaded
    trigger: '.o_hierarchy_article_name input:value("EditorCommandsArticle")',
}, { // use the template as description for the contact record
    trigger: "[data-embedded='clipboard'] button:contains(Use as)",
    run: 'click',
}, { // check that the content of the template was inserted as description
    trigger: '.o_form_sheet .o_field_html .odoo-editor-editable p:contains("Hello world")',
}];

registry.category("web_tour.tours").add('knowledge_article_commands_tour', {
    url: '/odoo',
    steps: () => [stepUtils.showAppsMenuItem(), {
    // open the Knowledge App
    trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
    run: "click",
},
    // Regular commands
    ...articleCommandSteps,
    ...fileCommandSteps,
    ...indexCommandSteps,
    ...tocCommandSteps,
    ...videoCommandSteps,
    ...clipboardCommandSteps,
    // Embed view commands
    ...embeddedViewPatchSteps,
    ...listCommandSteps,
    ...embedKanbanSteps,
    ...embedKanbanActWindowSteps,
    ...embedCardsKanbanSteps,
    // Misc
    ...embedViewFiltersSteps,
    ...embedKanbanEditArticleSteps,
    ...articleCommandUsageSteps,
    ...articleCommandComposerSteps,
    ...clipboardUsageSteps,  // has to stay last, see steps docstring
    ...unpatchSteps,
    ...endKnowledgeTour()
]});
