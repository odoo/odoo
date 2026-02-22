/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useStories } from "../stories";

export class Sidebar extends Component {
    static template = "pos_owlybook.Sidebar";

    setup() {
        this.stories = useStories();
        this.filterName = "";
        this.map = this.getAllStories();
        this.all = this.getStories_Folder_Module();
        this.filteredStories = useState([...this.all[0]]);
        this.filteredFolders = useState([...this.all[1]]);
        this.filteredModule = useState([...this.all[2]]);
    }

    /**
     * Show/hide the folder.
     * @param {Object} folder - An object with a "folded" boolean property.
     */
    toggleFold(folder) {
        folder.folded = !folder.folded;
    }

    /**
     * Executes when a story is clicked in the sidebar. Sends the information to the parent.
     * @param {Object} story - The story that has been clicked.
     */
    onStoryClick(story) {
        this.stories.setActive(story);
    }

    /**
     * This function iterate through the stories to create a Map that contains the folder has the key and a
     * list of stories has value.
     * @returns {Object} result - result is a Map following the structure {folder: [ story1, story2, ...]}
     */
    getAllStories() {
        const result = new Map();
        for (const name in this.stories.stories) {
            const innerResult = new Map();
            result.set(name, innerResult);
            const folder = this.stories.stories[name];
            for (const folderName in folder) {
                const file = folder[folderName];
                for (const fileName in file) {
                    innerResult.set(fileName, []);
                    const stories = file[fileName].stories;
                    for (let i = 0; i < stories.length; i++) {
                        const title = stories[i].title;
                        innerResult.get(fileName).push(title);
                    }
                }
            }
        }
        return result;
    }

    /**
     * This function iterate through the map and add the element to the list res_stories and the set res_folder
     * @returns {Object} res_stories, res_folders - res_stories is a list of items and res_folder is a set of items
     */
    getStories_Folder_Module() {
        const res_stories = [];
        const res_folder = new Set();
        const res_module = new Set();

        for (const [key, value] of this.map) {
            res_module.add(key);
            const innerMap = value;
            for (const [key, value] of innerMap) {
                res_folder.add(key);
                res_stories.push(value);
            }
        }
        return [res_stories.flat(), res_folder, res_module];
    }
}
