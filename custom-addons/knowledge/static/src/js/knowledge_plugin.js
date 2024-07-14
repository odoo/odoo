/** @odoo-module */

import { _t } from '@web/core/l10n/translation';
import { decodeDataBehaviorProps, getVideoUrl } from '@knowledge/js/knowledge_utils';
import { registry } from "@web/core/registry";

/**
 * Set of all the classes that needs to be cleaned before saving the article
 */
const DECORATION_CLASSES = new Set([
    'o_knowledge_header_highlight',
    'focused-comment'
]);
/**
 * Plugin for OdooEditor. This plugin will allow us to clean/transform the
 * document before saving it in the database.
 */
export class KnowledgePlugin {
    constructor ({ editor }) {
        this.editor = editor;
    }
    /**
     * Some content displayed as part of a Behavior Component render is not destined to be saved.
     * The purpose of this function is to clean such content so that it will not be saved nor considered
     * during _isDirty evaluation (which is the determining factor to enable a save).
     * @param {Element} editable
     */
    cleanForSave(editable) {
        // Remove the decoration classes from the editable:
        for (const decorationClass of DECORATION_CLASSES) {
            for (const elementToClean of editable.querySelectorAll(`.${decorationClass}`)) {
                elementToClean.classList.remove(decorationClass);
            }
        }
        // Replace the iframe with a video link, because iframe elements are discarded by the backend sanitizer,
        // and Behavior components are not rendered for public users, so they'll have access to the link instead
        for (const anchor of editable.querySelectorAll('.o_knowledge_behavior_type_video')) {
            const props = decodeDataBehaviorProps(anchor.dataset.behaviorProps);
            const a = document.createElement('a');
            a.href = getVideoUrl(props.platform, props.videoId, props.params);
            a.textContent = _t('Open Video');
            a.target = '_blank';
            while (anchor.firstChild) {
                anchor.removeChild(anchor.firstChild);
            }
            anchor.append(a);
        }
        // Remove the `d-none` class of the fileName element in case the
        // html_field is being saved while the user is editing the name of the
        // file (The input is removed by default because it is the child of a
        // data-oe-transient-content="true" node).
        for (const fileNameEl of editable.querySelectorAll('.o_knowledge_behavior_type_file .o_knowledge_file_name_container')) {
            fileNameEl.classList.remove("d-none");
        }

        // Remove the loading icon and/or error messages from embedded views anchors.
        // Only children used as a props for the Embedded View Component are kept.
        for (const embeddedViewEl of editable.querySelectorAll(".o_knowledge_behavior_type_embedded_view")) {
            const childrenToKeep = [...embeddedViewEl.querySelectorAll(":scope > [data-prop-name]")];
            embeddedViewEl.replaceChildren(...childrenToKeep);
        }
    }
}

registry.category("wysiwygPlugins").add("Knowledge", KnowledgePlugin);
