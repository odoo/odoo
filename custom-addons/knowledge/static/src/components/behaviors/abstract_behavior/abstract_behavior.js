/** @odoo-module */

import { useService } from "@web/core/utils/hooks";
import {
    Component,
    onMounted,
    useExternalListener,
} from "@odoo/owl";
import {
    copyOids,
    getPropNameNode,
} from "@knowledge/js/knowledge_utils";


export class AbstractBehavior extends Component {
    static props = {
        anchor: { type: Element },
        // HtmlElement children of the original anchor, before Component
        // rendering. They are the Elements that were used to extract html
        // props for this Behavior. This prop usage is to recover the OIDs set
        // by the editor on those nodes and to remove them from the DOM once
        // the mounting is done. Cases where the nodes possess a collaborative
        // OID to recover:
        // - received a node from a collaborator
        // - loaded the article as it is stored in the database in edit mode
        // - switching from readonly to edit mode
        // - undo/redo in the editor with the Behavior appearing/disappearing
        // - copy/paste, drag/drop elements with the Behavior
        blueprintNodes: { type: Array },
        // Hook for Behavior executed when they are mounted and synchronized
        // (have the correct oids for their collaborative nodes). Typically, it
        // is handled by the html_field and its purpose is to synchronously
        // insert the Behavior anchor at the correct position in the editable.
        // In edit mode, we cannot let OWL mount a Behavior directly in the
        // editable as it is an asynchronous process and the state of the html
        // field can change while the Behavior is being mounted (at that point
        // it has to be discarded).
        onReadyToInsertInEditor: { type: Function, optional: true },
        readonly: { type: Boolean },
        record: { type: Object },
        // Element containing all Behavior anchors. It can either be the
        // OdooEditor.editable, or the readonlyElementRef.el.
        root: { type: Element },
        wysiwyg: { type: Object, optional: true },
    };

    setup() {
        super.setup();
        this.setupAnchor();
        this.uiService = useService('ui');
        this.knowledgeCommandsService = useService('knowledgeCommandsService');
        if (!this.props.readonly) {
            onMounted(() => {
                // Reconstruct the blueprint as an Element outside the DOM, but
                // with the original nodes to keep their OIDs.
                const blueprint = this.props.anchor.cloneNode(false);
                // Remove blueprint nodes (not rendered by OWL) from the anchor
                // in the DOM, but keep them in order to extract useful oids
                // from them.
                blueprint.replaceChildren(...this.props.blueprintNodes);
                // hook for extra rendering steps for Behavior (not done by
                // OWL templating system).
                this.extraRender();
                if (this.props.anchor.oid) {
                    blueprint.oid = this.props.anchor.oid;
                    // copy OIDs from the blueprint in case those OIDs
                    // are used in collaboration.
                    // this step is done before the component is inserted in the
                    // editable (when it is still in the rendering zone)
                    this.synchronizeOids(blueprint);
                }
                // the rendering was done outside of the OdooEditor,
                // onReadyToInsertInEditor contains instructions on how to move
                // the mounted content in the editable.
                this.props.onReadyToInsertInEditor();
            });
        } else {
            onMounted(() => {
                // Remove blueprint nodes (not rendered by OWL) from the anchor
                // in the dom. It is the best timing to do it since their
                // removal will occur synchronously with the addition of OWL
                // nodes.
                this.props.blueprintNodes.forEach(child => child.remove());
            });
        }
    }

    //--------------------------------------------------------------------------
    // TECHNICAL
    //--------------------------------------------------------------------------

    /**
     * @abstract
     * This method is is a hook executed during the onMounted hook, but
     * before the rendered Behavior is inserted in the editor (in edit mode).
     * It can be useful to manually insert nodes that can not be managed by OWL
     * templating system (i.e. because they will be altered by the editor),
     * before being observed by the editor and/or assigned an oid.
     * @see ArticlesStructureBehavior for an example.
     *
     * Why should this hook be used:
     * - Some non-editable HTML content managed by the Behavior has to be
     *   shared in collaboration. This means that the content can be updated by
     *   a mutation received through the collaboration (and which is the result
     *   of a collaborator using a feature of the Behavior which changes its
     *   content, i.e. a refresh for the ArticlesStructureBehavior). Owl will
     *   crash if nodes it rendered are not replaced by an Owl patch, so that's
     *   why one should use this this hook to render that content and insert
     *   it where it belong inside the nodes already rendered by Owl for the
     *   first time.
     * - Ensure that the Behavior has a fully coherent state before being
     *   inserted in the editor and shared in collaboration as a single
     *   mutation.
     * - Avoid creating multiple "partial" steps that can mess up the history
     *   system (can Undo/Redo each step).
     */
    extraRender() {}

    /**
     * Normally, the editable is the only element in the editor which has the focus.
     * With behaviors however (and most notably embedded views), it can be useful to delegate the focus at a lower level
     * (i.e. to use hotkeys with the uiService).
     * Also, since "focus" and "blur" events don't bubble, and the "blur" event is used to handle a dirty field for saving purpose,
     * it has to sometimes be triggered programmatically for a proper save.
     *
     * We are adding tabindex="-1" to the anchor because this attribute is needed to capture the
     * 'focusin' and 'focusout' events.
     * In these events we are using activateElement/deactivateElement:
     *
     * `activateElement` is used to set the anchor as an active element in the ui service, this enables
     * us to contain the events inside the embedded view when it has the focus.
     *
     * `deactivateElement` removes the anchor as an active element, leaving only the document as active
     * and we come back to the default behavior of the document handling all the events.
     *
     */
    handleFocusEvents() {
        this.props.anchor.setAttribute('tabindex', '-1');
        useExternalListener(this.props.anchor, 'focusin', () => {
            if (!this.props.anchor.contains(this.uiService.activeElement)) {
                this.uiService.activateElement(this.props.anchor);
            }
        });
        useExternalListener(this.props.anchor, 'focusout', (event) => {
            if (!this.props.anchor.contains(event.relatedTarget)) {
                this.uiService.deactivateElement(this.props.anchor);
                if (!this.props.readonly && !this.editor.editable.contains(event.relatedTarget)) {
                    this.editor.editable.dispatchEvent(new FocusEvent('blur', {relatedTarget: event.relatedTarget}));
                }
            }
        });
    }

    /**
     * This method is used to ensure that the correct attributes are set
     * on the anchor of the Behavior. Attributes could be incorrect for the
     * following reasons: cleaned by the sanitization (frontend or backend),
     * attributes from a previous Odoo version, attributes from a drop/paste
     * of a Behavior which was in another state (i.e. from readonly to editable)
     */
    setupAnchor() {
        this.handleFocusEvents();
        if (!this.props.readonly) {
            this.props.anchor.setAttribute('contenteditable', 'false');
            // prevent some interactions with OdooEditor, @see web_editor module
            this.props.anchor.dataset.oeProtected = "true";
        }
    }

    /**
     * Every node in the editor has a unique oid in collaboration. This is to
     * identify to which node apply a mutation received from a collaborator.
     * This method reapplies the oids from the blueprint of the Behavior (nodes
     * present before it was mounted by Owl) to collaborative elements
     * (=elements under a node with data-oe-protected="false" in a Behavior),
     * after they were rendered by Owl.
     *
     * By default, only html props nodes (data-prop-name) are synchronized,
     * for other collaborative content, this method should be overridden to
     * specify which nodes need to be synchronized.
     *
     * @param {Element} blueprint node containing all original DOM nodes
     *                  from this.props.blueprintNodes.
     */
    synchronizeOids(blueprint) {
        // extract OIDs from `data-oe-protected='false'` elements which need to
        // be synchronized in collaborative mode from the blueprint.
        this.props.anchor.querySelectorAll('[data-oe-protected="false"][data-prop-name]').forEach(node => {
            const propName = node.dataset.propName;
            const blueprintElement = getPropNameNode(propName, blueprint);
            if (!blueprintElement) {
                return;
            }
            // copy OIDs from the blueprint for a collaborative
            // node of the behavior
            copyOids(blueprintElement, node);
        });
    }

    //--------------------------------------------------------------------------
    // GETTERS/SETTERS
    //--------------------------------------------------------------------------

    get editor () {
        return this.props.wysiwyg ? this.props.wysiwyg.odooEditor : undefined;
    }
}
