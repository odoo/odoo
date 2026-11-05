/** @odoo-module */

import { reactive, useState, useEnv, useSubEnv } from "@odoo/owl";
import { registry } from "@web/core/registry";
const storiesRegistry = registry.category("stories");
let stories = undefined;

function arrayToSelectMenuArray(choices) {
    return choices?.map((value) => {
        if (typeof value !== "object") {
            return { value, label: value };
        } else {
            return value;
        }
    });
}

export function useStories() {
    const env = useEnv();
    return useState(env.stories);
}

export function onEvent(name, args) {
    const params = {};
    for (let i = 0; i < args.length; i++) {
        params[`arg #${i}`] = args[i];
    }
    stories.active.events.push({ name, params });
}

export function setupStories(router) {
    stories = new Stories(router);
    const storyRegistry = storiesRegistry.getAll().sort(function (a, b) {
        return a.title.localeCompare(b.title);
    });
    for (const storyCategory of storyRegistry) {
        for (const story of storyCategory.stories) {
            const moduleName = storyCategory.module;
            const folder = storyCategory.title;
            if (!(moduleName in stories.stories)) {
                stories.stories[moduleName] = { folders: {} };
            }
            if (!(folder in stories.stories[moduleName]["folders"])) {
                stories.stories[moduleName]["folders"][folder] = { stories: [] };
            }
            const storiesConfig = story.storyConfig ? story.storyConfig : story;
            const parentComponent = story.storyConfig ? story : undefined;
            stories.stories[moduleName]["folders"][folder].stories.push({
                moduleName,
                folder,
                ...storiesConfig,
                parentComponent,
            });
        }
    }
    useSubEnv({ stories });
    return useStories();
}

export class Stories {
    constructor(router) {
        const self = reactive(this);
        self.setup(router);
        return self;
    }

    setup(router) {
        this.stories = {};
        this.active = {};
        this.router = router;
    }

    /**
     * Set the story passed in parameter as active.
     * The active story is read by the Owlybook to know which story to render.
     * Also deal with custom URL
     * @param {Object} story
     */
    setActive(story) {
        this.active = story;
        this.active.events = [];
        this.setupProps(story);
        const { module, folder, title } = story;
        this.router.pushState({ module, folder, title });
    }

    getStoryByDescription({ module, folder, title }) {
        const stories = this.stories[module]["folders"][folder].stories;
        for (const currentStory of stories) {
            if (currentStory.title === title) {
                return currentStory;
            }
        }
    }

    /**
     * Loop through the props definition of the component, the props options of the stories
     * and populate the processedProps of the story. The processedProps will be read and updated by
     * the Props component (panel) and read by the ComponentRenderer (canvas)
     * @param {Object} story
     */
    setupProps(story) {
        // Props static definition
        const propsDefinition = story.component.props;
        const propsDefinitionDefault = story.component.defaultProps || [];
        // props story configuration
        const propsStoryConfig = story.props;
        story.processedProps = {};

        for (const [propName, value] of Object.entries(propsDefinition)) {
            story.processedProps[propName] = {};
            const propsStoryObject = story.processedProps[propName];
            propsStoryObject.type = value.type;
            propsStoryObject.value = propsDefinitionDefault[propName];
            propsStoryObject.optional = value.optional || false;

            if (propsStoryConfig && propName in propsStoryConfig) {
                propsStoryObject.readonly = propsStoryConfig[propName].readonly || false;
                propsStoryObject.help = propsStoryConfig[propName].help || false;
                propsStoryObject.choices = arrayToSelectMenuArray(
                    propsStoryConfig[propName].choices
                );
                if ("value" in propsStoryConfig[propName]) {
                    propsStoryObject.value = propsStoryConfig[propName].value;
                }
            }
        }
    }

    /**
     * Build the `processedAttrs` of the story. `processedAttrs` contains the attributes shown in
     * the bottom panel for the modification of view attribute. This method is needed to manipulate
     * subAttributes such as the `options` attribute in many2one.
     * @param {Object} story
     */
    setupAttrs(story) {
        const attrsStoryConfig = story.attrs;
        story.processedAttrs = {};

        for (const [attrsName, value] of Object.entries(attrsStoryConfig)) {
            if (value.subAttrs) {
                for (const [subName, subValue] of Object.entries(attrsStoryConfig[attrsName])) {
                    if (subName !== "subAttrs") {
                        story.processedAttrs[`${attrsName}.${subName}`] = subValue;
                        story.processedAttrs[`${attrsName}.${subName}`].choices =
                            arrayToSelectMenuArray(
                                story.processedAttrs[`${attrsName}.${subName}`].choices
                            );
                    }
                }
            } else {
                story.processedAttrs[attrsName] = value;
                story.processedAttrs[attrsName].choices = arrayToSelectMenuArray(
                    story.processedAttrs[attrsName].choices
                );
            }
        }
    }
}
