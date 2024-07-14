/** @odoo-module */

import { HtmlField, htmlField } from "@web_editor/js/backend/html_field";
import { patch } from "@web/core/utils/patch";
import { templates, loadBundle } from "@web/core/assets";
import {
    copyOids,
    decodeDataBehaviorProps,
    getPropNameNodes,
} from "@knowledge/js/knowledge_utils";
import { debounce } from "@web/core/utils/timing";
import { Deferred, Mutex } from "@web/core/utils/concurrency";
import { useService } from "@web/core/utils/hooks";
import { useRecordObserver } from "@web/model/relational_model/utils";
import {
    App,
    markup,
    onWillDestroy,
    onWillUnmount,
    onWillUpdateProps,
    useEffect,
    useRef,
} from "@odoo/owl";

// Behaviors:

import { ArticleBehavior } from "@knowledge/components/behaviors/article_behavior/article_behavior";
import { ArticlesStructureBehavior } from "@knowledge/components/behaviors/articles_structure_behavior/articles_structure_behavior";
import { FileBehavior } from "@knowledge/components/behaviors/file_behavior/file_behavior";
import { EmbeddedViewBehavior } from "@knowledge/components/behaviors/embedded_view_behavior/embedded_view_behavior";
import { TemplateBehavior } from "@knowledge/components/behaviors/template_behavior/template_behavior";
import { TableOfContentBehavior } from "@knowledge/components/behaviors/table_of_content_behavior/table_of_content_behavior";
import { VideoBehavior } from "@knowledge/components/behaviors/video_behavior/video_behavior";
import { ViewLinkBehavior } from "@knowledge/components/behaviors/view_link_behavior/view_link_behavior";

const HtmlFieldPatch = {
    /**
     * @override
     */
    setup() {
        super.setup(...arguments);
        this.behaviorTypes = {
            o_knowledge_behavior_type_article: {
                Behavior: ArticleBehavior,
            },
            o_knowledge_behavior_type_file: {
                Behavior: FileBehavior,
            },
            o_knowledge_behavior_type_template: {
                Behavior: TemplateBehavior,
            },
            o_knowledge_behavior_type_toc: {
                Behavior: TableOfContentBehavior,
            },
            o_knowledge_behavior_type_articles_structure: {
                Behavior: ArticlesStructureBehavior
            },
            o_knowledge_behavior_type_embedded_view: {
                Behavior: EmbeddedViewBehavior
            },
            o_knowledge_behavior_type_view_link: {
                Behavior: ViewLinkBehavior
            },
            o_knowledge_behavior_type_video: {
                Behavior: VideoBehavior,
            },
        };
        this.uiService = useService('ui');
        this.behaviorState = {
            // Set of anchor elements with an active Behavior (Owl App) used to
            // keep track of them.
            appAnchors: new Set(),
            // Observer responsible for mounting Behaviors coming to the DOM,
            // and destroying those that are removed.
            appAnchorsObserver: new MutationObserver(() => {
                // Clean Behaviors that are not currently in the DOM.
                const anchors = this.behaviorState.observedElement.querySelectorAll('.o_knowledge_behavior_anchor');
                // If the DOM is altered manually (i.e. in a tour when using
                // `text` instruction on the html_field node, the handlerRef el
                // is removed, therefore we have to ensure that it exists).
                const hiddenMountedAnchors = [
                    ...(this.behaviorState.handlerRef.el?.querySelectorAll(
                        ".o_knowledge_behavior_anchor"
                    ) || []),
                ].filter((anchor) => {
                    return !anchor.oKnowledgeBehavior?.validator.obsolete;
                });
                this.destroyBehaviorApps(new Set([...anchors, ...hiddenMountedAnchors]));
                // Schedule a scan for new Behavior anchors to render.
                this.mountBehaviors();
                // Handle the changes for the comments
                if (!this.debouncedTriggerCommentsPositioning) {
                    this.debouncedTriggerCommentsPositioning = debounce(this.triggerCommentsPositioning, 500);
                }
                this.debouncedTriggerCommentsPositioning.cancel();
                this.debouncedTriggerCommentsPositioning();
            }),
            // Owl does not support destroying an App when its container node is
            // not in the DOM. This reference is a `d-none` element used to
            // re-insert anchors of live Behavior App before calling `destroy`
            // to circumvent the Owl limitation.
            handlerRef: useRef("behaviorHandler"),
            // Element currently being observed for Behaviors Components.
            observedElement: null,
            // Set of anchors that contains Behaviors that are obsolete for the
            // current state of the field, but are still mounted in the handler
            // element.
            obsoleteAnchors: new Set(),
            // Mutex to prevent multiple _mountBehaviors methods running at
            // once.
            updateMutex: new Mutex(),
            // Since _mountBehaviors function is asynchronous but onPatched and
            // onMounted are synchronous and do not wait for their content
            // to finish, the life cycle of the HTML field component can
            // continue while Behaviors are being mounted. At that point,
            // those not-yet-mounted Behaviors are obsolete and should be
            // discarded.
            validator: this.constructBehaviorsValidator(this.props),
        };
        this.boundMountBehaviors = this._onMountBehaviors.bind(this);
        this.knowledgeCommandsService = useService('knowledgeCommandsService');
        onWillDestroy(() => {
            this.behaviorState.validator.obsolete = true;
            this.behaviorState.appAnchorsObserver.disconnect();
            this.destroyBehaviorApps();
        });
        onWillUnmount(() => {
            this._removeMountBehaviorsListeners();
        });
        let previousArticleId;
        useRecordObserver((record, props) => {
            if (!previousArticleId || previousArticleId !== record.resId) {
                previousArticleId = record.resId;
                this.updateBehaviorsValidator(props);
            }
        });
        onWillUpdateProps((props) => {
            this.updateBehaviorsValidator(props);
        });
        useEffect(() => {
            this.updateBehaviorsValidator(this.props);
            // Update Behaviors and reset the observer when the html_field
            // DOM element changes.
            if (this.behaviorState.observedElement !== this.valueContainerElement) {
                // The observed Element has to be replaced.
                this.behaviorState.appAnchorsObserver.disconnect();

                this.behaviorState.observedElement = null;
                this.destroyBehaviorApps();
            }
            if (
                !this.behaviorState.observedElement &&
                this.valueContainerElement
            ) {
                // Restart the observer only if the html_field element is
                // ready to display its value. If it is not ready (async),
                // it will be started in @see startWysiwyg.
                this.startAppAnchorsObserver();
                this.mountBehaviors();
            }
        }, () => {
            return [
                this.props.readonly,
                this.props.record,
                this.valueContainerElement,
            ];
        });
    },

    triggerCommentsPositioning() {
        const allCommentsAnchors = this.valueContainerElement?.querySelectorAll('.knowledge-thread-comment');
        if(allCommentsAnchors) {
            this.env.bus.trigger('KNOWLEDGE_COMMENTS:CHANGES_DETECTED', {
                impactedComments: Array.from(allCommentsAnchors).map((node) => parseInt(node.dataset.id))
            });
        }
    },

    //--------------------------------------------------------------------------
    // GETTERS/SETTERS
    //--------------------------------------------------------------------------
    
    /**
     * Returns the container which holds the current value of the html_field
     * if it is already mounted and ready.
     *
     * @returns {HTMLElement}
     */
    get valueContainerElement() {
        if (this.props.readonly && this.readonlyElementRef.el) {
            return this.readonlyElementRef.el;
        } else if (this.wysiwyg?.odooEditor) {
            return this.wysiwyg.odooEditor.editable;
        }
        return null;
    },

    /**
     * The editor has to pause (collaborative) external steps when a new
     * Behavior (coming from an external step) has to be rendered, because
     * some of the following external steps could concern a rendered element
     * inside the Behavior. This override adds a callback for the editor to
     * specify when it should stop applying external steps (the callback
     * analyzes the editable, checks if a new Behavior has to be rendered, and
     * returns a promise resolved when that Behavior is rendered).
     *
     * @override
     */
    get wysiwygOptions() {
        const options = super.wysiwygOptions;
        /**
         * @param {Element} element to scan for new Behaviors
         * @returns {Promise|null} resolved when the mounting is done, or
         *                         null if there is nothing to mount
         */
        const mountCollaborativeBehaviors = (element) => {
            let behaviorsData = [];
            // Check that the mutex is idle synchronously to avoid unnecessary
            // overheads in the editor that would be caused by returning a
            // resolved Promise instead of null.
            if (!this.behaviorState.updateMutex._unlockedProm) {
                behaviorsData = this._scanFieldForBehaviors(element);
                if (!behaviorsData.length) {
                    return null;
                }
            }
            return this.mountBehaviors(behaviorsData, element);
        };
        options.postProcessExternalSteps = mountCollaborativeBehaviors;
        return options;
    },

    //--------------------------------------------------------------------------
    // HTMLFIELD STANDARD METHODS
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async startWysiwyg() {
        await super.startWysiwyg(...arguments);
        this.updateBehaviorsValidator(this.props);
        this._addMountBehaviorsListeners();
        this.startAppAnchorsObserver();
        await this.mountBehaviors();
        const behaviorBlueprint = this.knowledgeCommandsService.popPendingBehaviorBlueprint({
            model: this.props.record.resModel,
            field: this.props.name,
            resId: this.props.record.resId,
        });
        if (behaviorBlueprint) {
            this.wysiwyg.appendBehaviorBlueprint(behaviorBlueprint);
        }
    },

    /**
     * This function is called in the process of commitChanges and will disable
     * Behavior rendering and destroy all currently active Behaviors, because
     * the super function will do heavy changes in the DOM that are not
     * supported by OWL.
     * Behaviors rendering is re-enabled after the processing of the super
     * function is done, but Behaviors are not restarted (they will be in
     * updateValue, function that is called after _toInline if the html_field
     * is not in a destroyed Owl state).
     *
     * @override
     */
    async _toInline() {
        // Prevent any new Behavior rendering during `toInline` processing.
        this.behaviorState.appAnchorsObserver.disconnect();

        this._removeMountBehaviorsListeners();
        // Wait for the `udpateBehaviors` mutex to ensure that it is idle during
        // `toInline` processing (we don't want it to mess with DOM nodes).
        await this.behaviorState.updateMutex.getUnlockedDef();
        // Destroy all Behaviors because `toInline` will apply heavy changes
        // in the DOM that are not supported by OWL. The nodes generated by
        // OWL stay in the DOM as the html_field value, but are not managed
        // by OWL during the `toInline` processing.
        this.destroyBehaviorApps();
        await super._toInline(...arguments);
        // Reactivate Behavior rendering.
        this._addMountBehaviorsListeners();
        this.startAppAnchorsObserver();
    },

    /**
     * This method should stay quasi-synchronous and is not allowed to await
     * more than the super promise, because it is used in the process of an
     * urgentSave during a `beforeunload` handling, and the browser does not
     * let enough time to add many asynchronous calls, and definitely not enough
     * time for a rpc roundtrip.
     *
     * @override
     */
    async updateValue() {
        const promise = super.updateValue(...arguments);
        // Update Behaviors after the updateValue to ensure that they all are
        // properly mounted (they could have been destroyed by `_toInline`).
        promise.then(() => this.mountBehaviors());
        // Return the `super` promise, not the `then` promise, so that the
        // urgentSave can continue even when Behaviors are being mounted.
        return promise;
    },

    //--------------------------------------------------------------------------
    // BEHAVIORS ENGINE
    //--------------------------------------------------------------------------

    /**
     * Create a validator object that will invalidate obsolete Behaviors
     * being mounted when the state of the htmlField changes.
     * @param {Object} props
     * @returns {Object} validator
     */
    constructBehaviorsValidator(props) {
        return {
            obsolete: false,
            state: {
                readonly: props.readonly,
                recordResId: props.record.resId,
                valueContainerElement: this.valueContainerElement,
            },
        };
    },

    /**
     * Destroy a Behavior App.
     *
     * Considerations:
     * - To mount the Behavior App at a later time based on the same anchor
     * where it was destroyed, it is necessary to keep some Component nodes
     * inside. Since Owl:App.destroy removes all its Component nodes, this
     * method has to clone them beforehand to preserve them.
     * - An Owl App has to be destroyed in the DOM (Owl constraint), but the
     * OdooEditor has no hook to tell if a node will be removed or not.
     * Therefore this method can be called by a MutationObserver, at which point
     * the anchor is not in the DOM anymore and it has to be reinserted before
     * the App can be destroyed. It is done in a custom `d-none` element aside
     * the editable.
     * - Cloned child nodes can be re-inserted after the App destruction in the
     * anchor. It is important to do it even if the anchor is not in the DOM
     * anymore since that same anchor can be re-inserted in the DOM with an
     * editor `undo`.
     *
     * @param {HTMLElement} anchor in which the Behavior is mounted
     */
    destroyBehaviorApp(anchor) {
        // Deactivate the Element in UI service to prevent unwanted behaviors
        this.uiService.deactivateElement(anchor);
        // Preserve the anchor children since they will be removed by the
        // App destruction.
        const clonedAnchor = anchor.cloneNode(true);
        for (const node of clonedAnchor.querySelectorAll('[data-oe-transient-content=""], [data-oe-transient-content="true"]')) {
            node.remove();
        }
        let shouldBeRemoved = false;
        let shouldBeRestored = false;
        const parentNode = anchor.parentNode;
        if (this.behaviorState.handlerRef.el?.contains(anchor)) {
            // If the anchor of the mounted Behavior to destroy is in the
            // Handler element, no need to re-insert it in the document after
            // the destroy.
            shouldBeRemoved = true;
        } else if (!document.body.contains(anchor)) {
            // If anchor has a parent outside the DOM, it has to be given back
            // to its parent after being destroyed, so it is replaced by its
            // clone (to keep track of its position).
            if (parentNode) {
                parentNode.replaceChild(clonedAnchor, anchor);
                shouldBeRestored = true;
            } else {
                shouldBeRemoved = true;
            }
            if (this.behaviorState.handlerRef.el) {
                // A Component should always be destroyed in the DOM.
                this.behaviorState.handlerRef.el.append(anchor);
            } else {
                // Last resort if handlerRef.el was removed manually from the
                // DOM (i.e. by a `text` operation in a tour), the Behavior
                // will be destroyed in the document body.
                shouldBeRemoved = true;
                document.body.append(anchor);
            }
        }
        anchor.oKnowledgeBehavior.mountedPromise.resolve(false);
        anchor.oKnowledgeBehavior.destroy();
        delete anchor.oKnowledgeBehavior;
        if (shouldBeRemoved) {
            anchor.remove();
        } else if (shouldBeRestored) {
            // Give back the anchor to its original parent (before destroying).
            parentNode.replaceChild(anchor, clonedAnchor);
        }
        // Recover the child nodes from the clone because OWL removed all of
        // them, but they are necessary to re-render the Component later.
        // (it's the blueprint of the Behavior).
        anchor.replaceChildren(...clonedAnchor.childNodes);
        this.behaviorState.appAnchors.delete(anchor);
        this.behaviorState.obsoleteAnchors.delete(anchor);
    },

    /**
     * Destroy all currently active Behavior Apps except those which anchor
     * is in `ignoredAnchors`.
     *
     * @param {Set<Element>} ignoredAnchors optional - Set of anchors to ignore
     *        for the destruction of Behavior Apps
     */
    destroyBehaviorApps(ignoredAnchors=new Set()) {
        for (const anchor of Array.from(this.behaviorState.appAnchors)) {
            if (this.behaviorState.obsoleteAnchors.has(anchor) || !ignoredAnchors.has(anchor)) {
                this.destroyBehaviorApp(anchor);
            }
        }
    },

    /**
     * Invalidate Behaviors being mounted for a previous html field state and
     * construct a new validator if the state changed.
     * @param {Object} props
     */
    updateBehaviorsValidator(props) {
        const validator = this.constructBehaviorsValidator(props);
        if (
            Object.entries(this.behaviorState.validator.state).some(
                ([prop, value]) => validator.state[prop] !== value
            )
        ) {
            // Invalidate ongoing mounting of Behaviors.
            this.behaviorState.validator.obsolete = true;
            // Create a new validator for the next Behaviors.
            this.behaviorState.validator = validator;
        }
    },

    /**
     * Mount Behaviors in visible anchors that should contain one.
     *
     * Since any mutation can trigger an mountBehaviors call, the mutex ensure
     * that the next mountBehaviors call always await the previous one.
     *
     * @param {Array[Object]} behaviorsData - optional - Contains information on
     *                        which Behavior to update. If not set, the
     *                        html_field will handle every visible Behavior
     *                        Composed by:
     *     @param {HTMLElement} [behaviorsData.anchor] Element which content
     *                          will be replaced by the rendered Component
     *                          (Behavior)
     *     @param {string} [behaviorsData.behaviorType] Class name of the
     *                      Behavior @see behaviorTypes
     *     edit mode only options:
     *     @param {string} [behaviorsData.behaviorStatus] optional - Depending
     *                     on how the Behavior is inserted, it should be handled
     *                     differently. Statuses:
     * - undefined:        - No need for extra care, the anchor is and
     *                       will stay present in the editable until the
     *                       Behavior finishes being mounted
     * - 'new':            - Result of a wysiwyg command, the anchor is not
     *                       in the editable and as such there is no OID to
     *                       recover from the blueprint (html value before
     *                       Component rendering)
     *     @param {Function} [behaviorsData.insert] optional - Instructions on
     *                       how to insert the Behavior when it is mounted.
     *                       Takes the anchor Element to be inserted as an
     *                       argument and returns an Array of inserted elements
     *                       or null if it fails.
     *     @param {Function} [behaviorsData.restoreSelection] optional - Method
     *                       to restore the selection in the editable before
     *                       inserting the rendered Behavior at the correct
     *                       position (where the user typed the command).
     *                       It returns an Array position @see setPosition or
     *                       null if it fails.
     *     @param {boolean} [behaviorsData.shouldSetCursor] optional - Whether
     *                      to use the setCursor method of the Behavior if it
     *                      has one when it is mounted and inserted in the
     *                      editable
     * @param {HtmlElement} target - optional - the node to scan for new
     *                      Behavior to instantiate. Defaults to
     *                      this.valueContainerElement
     * @returns {Promise} Resolved when the mutex updating Behaviors is idle.
     */
    async mountBehaviors(behaviorsData = [], target = null) {
        for (const behaviorData of behaviorsData) {
            behaviorData.validator = this.behaviorState.validator;
        }
        this.behaviorState.updateMutex.exec(() => this._mountBehaviors(behaviorsData, target));
        return this.behaviorState.updateMutex.getUnlockedDef();
    },

    async _mountBehaviors(behaviorsData, target) {
        if (
            (target && !document.body.contains(target)) ||
            !document.body.contains(this.valueContainerElement) ||
            !document.body.contains(this.behaviorState.handlerRef.el)
        ) {
            // Validate that the working environment is ready.
            return;
        }
        const renderingContainerElement = (this.props.readonly) ? target || this.readonlyElementRef.el : this.behaviorState.handlerRef.el;
        target = target || this.valueContainerElement;
        if (!behaviorsData.length) {
            behaviorsData = this._scanFieldForBehaviors(target);
        }
        const promises = [];
        for (const behaviorData of behaviorsData) {
            const {Behavior} = this.behaviorTypes[behaviorData.behaviorType] || {};
            if (
                !Behavior ||
                behaviorData.validator.obsolete ||
                // If a Behavior is already instantiated, no need to redo-it.
                behaviorData.anchor.oKnowledgeBehavior
            ) {
                continue;
            }
            // `anchor` is the node inside which the Component will be mounted.
            const anchor = this._prepareBehaviorAnchor(behaviorData, renderingContainerElement);
            // Prepare the props passed to the Behavior Component.
            const props = this._prepareBehaviorProps(Behavior, behaviorData, anchor);
            if (!props) {
                // If an error occured when preparing the Behavior props, stop
                // trying to mount it.
                continue;
            }
            // Extract the configuration from the Odoo main Owl App to use it
            // for the Behavior App.
            const config = (({env, dev, translatableAttributes, translateFn}) => {
                return { env, dev, translatableAttributes, translateFn };
            })(this.__owl__.app);
            anchor.oKnowledgeBehavior = new App(Behavior, {
                ...config,
                templates,
                props,
            });
            this.behaviorState.appAnchors.add(anchor);
            anchor.oKnowledgeBehavior.validator = this.behaviorState.validator;
            // App.mount is not resolved if the App is destroyed before it
            // is mounted, so instead, await a Deferred that is resolved
            // when the App is mounted (true) or destroyed (false).
            anchor.oKnowledgeBehavior.mountedPromise = new Deferred();
            anchor.oKnowledgeBehavior.mount(anchor).then(
                // Resolve the mounting promise if the App was not already
                // destroyed.
                () => anchor.oKnowledgeBehavior?.mountedPromise.resolve(true)
            );
            const promise = anchor.oKnowledgeBehavior.mountedPromise.then(async (isMounted) => {
                // isMounted is true if the App was mounted and false if it
                // was destroyed before being mounted. If it was mounted,
                // update child behaviors inside anchor
                if (isMounted) {
                    await this._mountBehaviors([], anchor);
                }
            });
            promises.push(promise);
        }
        await Promise.all(promises);
    },

    /**
     * Configuration of the node in which the Behavior will be mounted.
     *
     * @param {Object} behaviorData @see mountBehaviors
     * @param {Element} renderingContainerElement Container in which the
     *                  Behavior anchor node is when it is mounted
     * @returns {Element} anchor in which the Behavior will be mounted
     */
    _prepareBehaviorAnchor(behaviorData, renderingContainerElement) {
        let anchor;
        if (this.props.readonly) {
            // Readonly mode, mounting is done in place.
            anchor = behaviorData.anchor;
        } else if (behaviorData.behaviorStatus === 'new') {
            // Edit mode, Behavior comes from a /command. Mounting is done in
            // the Handler in the provided element which is not yet in the DOM.
            anchor = behaviorData.anchor;
            renderingContainerElement.append(anchor);
        } else {
            // Edit mode, Behavior comes from an anchor already in the DOM.
            // Mounting is done in the Handler in a clone, and the insertion
            // should swap the clone with the original node.
            // Copy the current state of the Behavior blueprint
            // before it is modified, in order to save the current
            // OIDs and recover them when the Component is rendered.
            anchor = copyOids(behaviorData.anchor);
            renderingContainerElement.append(anchor);
            behaviorData.insert = (anchor) => {
                if (this.wysiwyg.odooEditor.editable.contains(behaviorData.anchor)) {
                    // Ignore the insertion if the mounted element
                    // cannot be moved in the DOM.
                    this.wysiwyg.odooEditor.observerUnactive('mount_knowledge_behaviors');
                    behaviorData.anchor.parentElement.replaceChild(anchor, behaviorData.anchor);
                    // Bypass the editor observer, so oids have to be set
                    // manually.
                    this.wysiwyg.odooEditor.idSet(anchor);
                    this.wysiwyg.odooEditor.observerActive('mount_knowledge_behaviors');
                    return [anchor];
                }
            };
        }
        return anchor;
    },

    /**
     * Prepare the Behavior Component props.
     *
     * @param {Class} Behavior The Behavior Class that will be instantiated
     * @param {Object} behaviorData @see mountBehaviors
     * @param {Element} anchor Node in which the Behavior will be mounted
     * @returns {Object} props to be given to the Behavior Component. Returns
     *                   null if the Behavior can not be mounted.
     *                  
     */
    _prepareBehaviorProps(Behavior, behaviorData, anchor) {
        // Default props for every Behavior.
        const props = {
            readonly: this.props.readonly,
            anchor: anchor,
            wysiwyg: this.wysiwyg,
            record: this.props.record,
            // readonlyElementRef.el or editable
            root: this.valueContainerElement,
            // Nodes which have necessary oids for the editor. Those nodes
            // should also be removed from the anchor during the insertion
            // process. In edit mode, those are clones taken from the blueprint,
            // To avoid a case where the original childNodes are modified during
            // Behavior mounting.
            blueprintNodes: [...anchor.childNodes],
        };
        let behaviorProps = {};
        if (anchor.hasAttribute("data-behavior-props")) {
            // Parse non-html props stored on the anchor of the Behavior as the
            // value of the data-behavior-props attribute.
            try {
                behaviorProps = decodeDataBehaviorProps(anchor.dataset.behaviorProps);
            } catch (error){
                // If data-behavior-props can not be decoded, ignore it and stop
                // trying to mount this Behavior for this call.
                if (this.env.debug) {
                    console.warn(`Error during Behavior props parsing, it will be displayed raw.`, anchor, error);
                }
                return null;
            }
        }
        // Add html props of the Behavior, each one of them is stored in a
        // (sub-)child element of the anchor with the attribute
        // data-prop-name, the name of the prop is the attribute value, and
        // the value of the prop is the content of that node).
        const propNodes = getPropNameNodes(anchor);
        for (const node of propNodes) {
            // Safe because sanitized by the editor and backend.
            behaviorProps[node.dataset.propName] = markup(node.innerHTML);
        }
        // Filter props to keep only the ones from the schema.
        for (const prop in behaviorProps) {
            if (prop in Behavior.props) {
                props[prop] = behaviorProps[prop];
            }
        }
        if (!this.props.readonly) {
            // Callback to insert a mounted Behavior in the editable.
            props.onReadyToInsertInEditor = () => {
                const cancelInsertion = () => {
                    this.behaviorState.obsoleteAnchors.add(anchor);
                };
                if (
                    behaviorData.validator.obsolete ||
                    (behaviorData.restoreSelection && !behaviorData.restoreSelection())
                ) {
                    return cancelInsertion();
                }
                const insertedNodes = behaviorData.insert ?
                    behaviorData.insert(anchor) :
                    this.wysiwyg.odooEditor.execCommand('insert', anchor);
                if (!insertedNodes) {
                    return cancelInsertion();
                }
                if (behaviorData.shouldSetCursor && anchor.oKnowledgeBehavior.root.component.setCursor) {
                    anchor.oKnowledgeBehavior.root.component.setCursor();
                }
                return insertedNodes;
            };
        }
        return props;
    },

    /**
     * Scans the target for Behaviors to mount.
     *
     * @param {HTMLElement} target Element to scan for Behaviors
     * @returns {Array[Object]} Array filled with the results of the scan.
     *          Any Behavior that is not instantiated at the moment of the scan
     *          will have one entry added in this Array, with the condition that
     *          it is not a child of another Behavior that is not mounted yet
     *          (those will have to be scanned again when their parent is
     *          mounted, because their anchor will change). Existing items of
     *          the Array will not be altered.
     */
    _scanFieldForBehaviors(target) {
        const behaviorsData = [];
        const types = new Set(Object.getOwnPropertyNames(this.behaviorTypes));
        const anchors = target.querySelectorAll('.o_knowledge_behavior_anchor');
        const anchorsSet = new Set(anchors);
        // Iterate over the list of nodes while the set will be modified.
        // Only keep anchors of Behaviors that have to be rendered first.
        for (const anchor of anchors) {
            if (!anchorsSet.has(anchor)) {
                // anchor was already removed (child of another anchor)
                continue;
            }
            if (anchor.oKnowledgeBehavior) {
                anchorsSet.delete(anchor);
            } else {
                // If the Behavior in anchor is not already mounted, remove
                // its children Behaviors from the scan, as their anchor will
                // change when this Behavior is mounted (replace all children
                // nodes by their mounted version). They will be mounted after
                // their parent during _mountBehaviors.
                const anchorSubNodes = anchor.querySelectorAll('.o_knowledge_behavior_anchor');
                for (const anchorSubNode of anchorSubNodes) {
                    anchorsSet.delete(anchorSubNode);
                }
            }
        }
        for (const anchor of anchorsSet) {
            const type = Array.from(anchor.classList).find(className => types.has(className));
            if (type) {
                behaviorsData.push({
                    anchor: anchor,
                    behaviorType: type,
                    validator: this.behaviorState.validator,
                });
            }
        }
        return behaviorsData;
    },
    async _lazyloadWysiwyg() {
        await super._lazyloadWysiwyg(...arguments);
        let wysiwygModule = await odoo.loader.modules.get('@knowledge/js/wysiwyg');
        if (!wysiwygModule) {
            await loadBundle('knowledge.assets_wysiwyg');
        }
    },

    /**
     * Observe the element containing the html_field value in the DOM.
     * Since that element can change during the lifetime of the html_field, the
     * observed element has to be held in a custom property (typically to
     * disconnect the observer).
     */
    startAppAnchorsObserver() {
        this.behaviorState.observedElement = this.valueContainerElement;
        this.behaviorState.appAnchorsObserver.observe(this.behaviorState.observedElement, {
            subtree: true,
            childList: true,
        });
    },

    //--------------------------------------------------------------------------
    // HANDLERS
    //--------------------------------------------------------------------------

    _addMountBehaviorsListeners() {
        if (this.wysiwyg?.odooEditor?.editable) {
            this.wysiwyg.odooEditor.editable.addEventListener('mount_knowledge_behaviors', this.boundMountBehaviors);
        }
    },

    _onMountBehaviors(ev) {
        const {behaviorData} = ev.detail || {};
        this.mountBehaviors((behaviorData) ? [behaviorData] : []);
    },

    _removeMountBehaviorsListeners() {
        if (this.wysiwyg?.odooEditor?.editable) {
            this.wysiwyg.odooEditor.editable.removeEventListener('mount_knowledge_behaviors', this.boundMountBehaviors);
        }
    },
};

patch(HtmlField.prototype, HtmlFieldPatch);

patch(htmlField, {
    extractProps(fieldInfo) {
        const props = super.extractProps(...arguments);
        props.wysiwygOptions.knowledgeCommands = fieldInfo.options.knowledge_commands;
        if ('allowCommandFile' in fieldInfo.options) {
            props.wysiwygOptions.allowCommandFile = Boolean(fieldInfo.options.allowCommandFile);
        }
        return props;
    },
});
