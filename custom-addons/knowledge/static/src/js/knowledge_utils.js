/** @odoo-module **/

import { loadEmoji } from "@web/core/emoji_picker/emoji_picker";
import {
    useComponent,
    useEffect,
    useRef,
} from "@odoo/owl";


// List of icons that should be avoided when adding a random icon
const iconsBlocklist = ["💩", "💀", "☠️", "🤮", "🖕", "🤢", "😒"];

/**
 * Get a random icon (that is not in the icons blocklist)
 * @returns {String} emoji
 */
export async function getRandomIcon() {
    const { emojis } = await loadEmoji();
    const randomEmojis = emojis.filter((emoji) => !iconsBlocklist.includes(emoji.codepoints));
    return randomEmojis[Math.floor(Math.random() * randomEmojis.length)].codepoints;
}

/**
 * Deep clone of a Behavior anchor (blueprint) ensuring that nodes with a
 * certain `data-prop-name` value are the only ones with that value. In case of
 * duplicates, only the last node is kept.
 *
 * @param {Element} anchor of a Behavior (not modified)
 * @returns {Element} blueprint deep copy of the anchor, filtered from duplicate
 *          data-prop-name values
 */
export function cloneBehaviorBlueprint(anchor) {
    const blueprint = anchor.cloneNode(true);
    const propNodes = getPropNameNodes(blueprint);
    const propNames = new Set();
    for (let i = propNodes.length - 1; i >= 0; i--) {
        const propName = propNodes[i].dataset.propName;
        if (propNames.has(propName)) {
            // Remove nodes with duplicate propName from the blueprint.
            propNodes[i].remove();
        } else {
            propNames.add(propName);
        }
    }
    return blueprint;
}

/**
 * Copy editor oids from source nodes to destination nodes. Delete destination
 * nodes ouids. This function can be used to synchronize oids on local nodes
 * from nodes received in collaboration, or to make a backup of local oids
 * before an OWL re-rendering (that would remove those oids and break
 * collaboration).
 *
 * @param {Element} source
 * @param {Element} [destination] optional destination node (deep clone if not
 *                  provided)
 * @returns {Element} destination with source oids
 */
export function copyOids(source, destination) {
    if (!destination) {
        destination = cloneBehaviorBlueprint(source);
    }
    const overrideOids = function (original, copy) {
        if (!copy || !original) {
            if (odoo.debug) {
                console.warn(`Oids synchronization failed, mismatch between source and destination nodes. Some elements may not be shared properly in collaboration.`);
            }
            return;
        }
        copy.oid = original.oid;
        delete copy.ouid;
        if (copy.nodeType === Node.ELEMENT_NODE && copy.firstChild && original.firstChild) {
            overrideOids(original.firstChild, copy.firstChild);
        }
        if (copy.nextSibling && original.nextSibling) {
            overrideOids(original.nextSibling, copy.nextSibling);
        }
    }
    overrideOids(source, destination);
    return destination;
}

/**
 * Convert the string from a data-behavior-props attribute to an usable object.
 *
 * @param {String} dataBehaviorPropsAttribute utf-8 encoded JSON string
 * @returns {Object} object containing props for a Behavior to store in the
 *                   html_field value of a field
 */
export function decodeDataBehaviorProps(dataBehaviorPropsAttribute) {
    return JSON.parse(decodeURIComponent(dataBehaviorPropsAttribute));
}

/**
 * Convert an object destined to be used as the value of a data-behavior-props
 * attribute to an utf-8 encoded JSON string (so that there is no special
 * character that would be sanitized by i.e. DOMPurify).
 *
 * @param {Object} dataBehaviorPropsObject object containing props for a
 *                 Behavior to store in the html_field value of a field
 * @returns {String} utf-8 encoded JSON string
 */
export function encodeDataBehaviorProps(dataBehaviorPropsObject) {
    return encodeURIComponent(JSON.stringify(dataBehaviorPropsObject));
}

/**
 * Return any existing propName node owned by the Behavior related to `anchor`.
 * Filter out propName nodes owned by children Behavior.
 *
 * @param {string} propName name of the htmlProp
 * @param {Element} anchor node to search for propName children
 * @returns {Element} last matching node (there should be only one, but it's
 *           always the last one that is taken as the effective prop)
 */
export function getPropNameNode(propName, anchor) {
    const propNodes = anchor.querySelectorAll(`[data-prop-name="${propName}"]`);
    for (let i = propNodes.length - 1; i >= 0; i--) {
        const closest = propNodes[i].closest('.o_knowledge_behavior_anchor');
        if (closest === anchor) {
            return propNodes[i];
        }
    }
}

/**
 * Get all anchor children with `data-prop-name` attribute which are
 * props of the anchor's own Behavior and not of other Behavior children.
 * (a Behavior can contain others).
 * @param {Element} anchor
 * @returns {Array<Element>} propNameNodes
 */
export function getPropNameNodes(anchor) {
    const propNodes = [];
    const candidates = anchor.querySelectorAll("[data-prop-name]");
    const subAnchors = [...anchor.querySelectorAll(".o_knowledge_behavior_anchor")];
    // Remove prop nodes of child-Behaviors (a Behavior can contain others).
    for (const propNode of candidates) {
        if (!subAnchors.some(subAnchor => subAnchor.contains(propNode))) {
            propNodes.push(propNode);
        }
    }
    return propNodes;
}

/**
 * @param {string} platform
 * @param {string} videoId
 * @param {Object} params
 * @throws {Error} if the given video config is not recognized
 * @returns {URL}
 */
export function getVideoUrl (platform, videoId, params) {
    let url;
    switch (platform) {
        case "youtube":
            url = new URL(`https://www.youtube.com/embed/${videoId}`);
            break;
        case "vimeo":
            url = new URL(`https://player.vimeo.com/video/${videoId}`);
            break;
        case "dailymotion":
            url = new URL(`https://www.dailymotion.com/embed/video/${videoId}`);
            break;
        case "instagram":
            url = new URL(`https://www.instagram.com/p/${videoId}/embed`);
            break;
        case "youku":
            url = new URL(`https://player.youku.com/embed/${videoId}`);
            break;
        default:
            throw new Error();
    }
    url.search = new URLSearchParams(params);
    return url;
}

/**
 * Set an intersection observer on the given element. This function will ensure
 * that the given callback function will be called at most once when the given
 * element becomes visible on screen. This function can be used to load
 * components lazily (see: 'EmbeddedViewBehavior').
 * @param {HTMLElement} element
 * @param {Function} callback
 * @returns {IntersectionObserver}
 */
export function setIntersectionObserver (element, callback) {
    const options = {
        root: null,
        rootMargin: '0px'
    };
    const observer = new window.IntersectionObserver(entries => {
        const entry = entries[0];
        if (entry.isIntersecting) {
            observer.unobserve(entry.target);
            callback();
        }
    }, options);
    observer.observe(element);
    return observer;
}

/**
 * This hook can be used on a Behavior template 'ref' (provided name) to
 * restrict its content to a single Element. The use case is the following:
 * - The template contains a `data-oe-protected="false"` element which content
 *   is determined programmatically (contenteditable="false") that can change
 *   during edition and which changes should be shared in collaboration.
 * - A collaborative change creates an history step that can be undone with
 *   the `undo` feature of the editor. Here, since the uniqueness of the
 *   child nodes has to be guaranteed, this hook adds a control feature to
 *   ensure this is the case: a mutation can only be undone if the last change
 *   was made by the user that is doing the undo. If the last change is an
 *   external collaborative step, undo will be prevented (because in that
 *   case the content would be 2 nodes, one per user, and that would be an
 *   inconsistent state for the element).
 *
 * Warning: Can only be used on a Component which implements AbstractBehavior.
 *
 * @param {string} name of the `t-ref` element in the Behavior template
 * @param {(element | undefined) => void} onChanged callback when the contents
 *        of the ref changed. If there is currently an element, it is provided
 *        as the argument, if there is no element, `undefined` is provided.
 * @returns
 */
export function useRefWithSingleCollaborativeChild(name, onChanged) {
    const component = useComponent();
    const ref = useRef(name);
    if (component.props.readonly) {
        // static content if readonly, no need for the observer.
        return ref;
    }
    let observedContent;
    const contentObserver = new MutationObserver(mutationList => {
        const newEls = new Set();
        const newNodes = new Set();
        for (const mutation of mutationList) {
            for (const node of mutation.addedNodes) {
                if (node.nodeType === Node.ELEMENT_NODE) {
                    newEls.add(node);
                } else {
                    newNodes.add(node);
                }
            }
        }
        if (newNodes.size) {
            // Clean up direct children that are not instances of Element, as
            // the only child (if any) should be an Element.
            component.editor.observerUnactive('knowledge_useRefWithSingleCollaborativeChild');
            for (const node of newNodes) {
                node.remove();
            }
            component.editor.observerActive('knowledge_useRefWithSingleCollaborativeChild');
        }
        const currentEls = Array.from(observedContent.querySelectorAll(':scope > *'));
        if (currentEls.length > 1) {
            // This use case occurs if multiple collaborators provide a mutation
            // adding a child element then undo their changes in the editor.
            // A user can never remove a node added by a collaborator using
            // `undo`, so if the last collaborator step was replacing a node
            // from the current user by one of his own, when the current user
            // triggers `undo`, his node is added back, but the collaborator
            // node is not removed, resulting in 2 children elements, which is
            // not desirable.
            // The rule imposed here is that if such a case occurs, the last
            // added element is kept, and the one recovered by `undo` is
            // discarded (resulting in virtually "no change").
            const previousEl = currentEls.find(el => !newEls.has(el)) || currentEls[0];
            component.editor.observerUnactive('knowledge_useRefWithSingleCollaborativeChild');
            observedContent.replaceChildren(previousEl);
            component.editor.observerActive('knowledge_useRefWithSingleCollaborativeChild');
        } else {
            onChanged(currentEls.at(0));
        }
    });
    useEffect(() => {
        // Update the observer when OWL changes the instance Element of
        // the `ref`
        if (ref.el) {
            observedContent = ref.el;
            contentObserver.observe(observedContent, {
                childList: true,
            });
        }
        return () => contentObserver.disconnect();
    }, () => [ref.el]);
    return ref;
}
