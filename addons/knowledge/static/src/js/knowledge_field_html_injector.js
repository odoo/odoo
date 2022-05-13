/** @odoo-module */
import Widget from 'web.Widget';
import { ComponentWrapper, WidgetAdapterMixin } from 'web.OwlCompatibility';
import { useService } from "@web/core/utils/hooks";
import { TemplateToolbar, FileToolbar } from './knowledge_toolbars';
import { ArticleBehavior, ContentsContainerBehavior } from './knowledge_behaviors';
const { Component } = owl;

/**
 * Component used to access the @see uiService
 */
class FieldHtmlInjectorComponent extends Component {
    setup() {
        this.uiService = useService('ui');
    }
}
FieldHtmlInjectorComponent.template = 'knowledge.injector_component';
/**
 * Widget used along @see FieldHtml to inject specific @see KnowledgeBehavior
 * and/or @see KnowledgeToolbar for specific blocks elements. These behaviors
 * can be used in both edit and readonly modes, and will contribute to a more
 * interactive @see FieldHtml . Toolbars added through this injector will be
 * cleaned before save through the @see KnowledgePlugin and won't be part of
 * the field final value.
 */
const FieldHtmlInjector = Widget.extend(WidgetAdapterMixin, {
    custom_events: {
        toolbar_removed: '_onToolbarRemoved',
        behavior_removed: '_onBehaviorRemoved',
    },
    /**
     * Map classes used in @see OdooEditor blocks to their corresponding
     * @see KnowledgeToolbar and template.
     */
    toolbar_types: {
        o_knowledge_toolbar_type_template: {
            template: 'knowledge.template_toolbar',
            Toolbar: TemplateToolbar,
        },
        o_knowledge_toolbar_type_file: {
            template: 'knowledge.file_toolbar',
            Toolbar: FileToolbar,
        },
    },
    /**
     * Map classes used in @see OdooEditor blocks to their corresponding
     * @see KnowledgeBehavior
     */
    behavior_types: {
        o_knowledge_behavior_type_contents_container: {
            Behavior: ContentsContainerBehavior,
        },
        o_knowledge_behavior_type_article: {
            Behavior: ArticleBehavior,
        },
    },
    /**
     * @override
     * @param {Widget} parent
     * @param {string} mode edit/readonly
     * @param {Element} field content of the @see FieldHtml
     * @param {Object} editor @see OdooEditor
     */
    init: function (parent, mode, field, editor) {
        this._super.apply(this, arguments);
        // store every toolbar anchor elements
        this.toolbar_anchors = new Set();
        // store every behavior anchor elements
        this.behavior_anchors = new Set();
        this.mode = mode;
        this.field = field;
        this.editor = editor;
    },
    /**
     * Start the injection process and setup injection event listeners.
     * The component is used to access uiService. This widget should be
     * converted to a component. TODO ABD
     * @see owl_compatibility
     *
     * @override
     */
    start: function () {
        const prom = this._super.apply(this, arguments);
        this.component = new ComponentWrapper(this, FieldHtmlInjectorComponent, {});
        const componentPromise = this.component.mount(this.el);
        $(this.field).on('refresh_injector', this._onRefreshInjector.bind(this));
        return Promise.all([prom, componentPromise]).then(function() {
            this.manageBehaviors();
            return this.manageToolbars();
        }.bind(this));
    },
    /**
     * @see owl_compatibility
     */
    update: function () {
        return this.component.update({});
    },
    /**
     * Setup the behavior injection process
     */
    manageBehaviors: function() {
        $(this.field).on('refresh_behaviors', this._onRefreshBehaviors.bind(this));
        this.updateBehaviors();
    },
    /**
     * Setup the toolbar injection process
     *
     * @returns {Promise} promise to append the initial batch of
     *                    @see KnowledgeToolbar
     */
    manageToolbars: function() {
        $(this.field).on('refresh_toolbars', this._onRefreshToolbars.bind(this));
        return this.updateToolbars();
    },
    /**
     * Scan this.field for every Toolbar container and anchor. Remove and
     * destroy currently registered obsolete toolbars.
     *
     * @param {Array[Object]} toolbarsData array to be filled with data
     *                                     currently present in this.field
     */
    _scanFieldForToolbars: function (toolbarsData) {
        const anchors = new Set();
        const types = new Set(Object.getOwnPropertyNames(this.toolbar_types));
        this.field.querySelectorAll('.o_knowledge_toolbars_container').forEach(function (types, container) {
            container.querySelectorAll('.o_knowledge_toolbar_anchor').forEach(function (types, container, anchor) {
                const type = Array.from(anchor.classList).find(className => types.has(className));
                if (type) {
                    toolbarsData.push({
                        container: container,
                        anchor: anchor,
                        type: type,
                    });
                    anchors.add(anchor);
                }
            }.bind(this, types, container));
        }.bind(this, types));
        // difference between the stored set and the computed one
        const differenceAnchors = new Set([...this.toolbar_anchors].filter(anchor => !anchors.has(anchor)));
        // remove obsolete toolbars
        differenceAnchors.forEach(anchor => {
            if (anchor.oKnowledgeToolbar) {
                anchor.oKnowledgeToolbar.removeToolbar();
            }
        });
    },
    /**
     * If toolbarsData is set, update only those toolbars, if not, recompute
     * every Toolbar of this.field
     *
     * @param {Array[Object]} toolbarsData
     * @param {Element} [container] element which has a toolbar anchor
     * @param {Element} [anchor] element in which to inject the toolbar
     * @param {string} [type] html class representing the toolbar type
     *                        (i.e.: @see o_knowledge_toolbar_type_... )
     * @returns {Promise} promise to append toolbars
     */
    updateToolbars: function (toolbarsData = []) {
        if (this.editor) {
            this.editor.observerUnactive();
        }
        if (!toolbarsData.length) {
            // no toolbarsData, recreate the array from the field value
            this._scanFieldForToolbars(toolbarsData);
        }

        // inject new toolbars
        const promises = [];
        toolbarsData.forEach(toolbarData => {
            const anchor = toolbarData.anchor;
            if (!anchor.oKnowledgeToolbar) {
                promises.push(this._createToolbar(toolbarData));
            } else {
                this.toolbar_anchors.add(anchor);
            }
        });

        return Promise.all(promises).then(() => {
            if (this.editor) {
                this.editor.observerActive();
            }
        });
    },
    /**
     * Scan this.field for every Behavior anchor. delete currently registered
     * obsolete behaviors.
     *
     * @param {Array[Object]} behaviorsData array to be filled with data
     *                                      currently present in this.field
     */
    _scanFieldForBehaviors: function (behaviorsData) {
        const anchors = new Set();
        const types = new Set(Object.getOwnPropertyNames(this.behavior_types));
        this.field.querySelectorAll('.o_knowledge_behavior_anchor').forEach(function (types, anchor) {
            const type = Array.from(anchor.classList).find(className => types.has(className));
            if (type) {
                behaviorsData.push({
                    anchor: anchor,
                    type: type,
                });
                anchors.add(anchor);
            }
        }.bind(this, types));
        // difference between the stored set and the computed one
        const differenceAnchors = new Set([...this.behavior_anchors].filter(anchor => !anchors.has(anchor)));
        // remove obsolete behaviors
        differenceAnchors.forEach(anchor => {
            if (anchor.oKnowledgeBehavior) {
                anchor.oKnowledgeBehavior.removeBehavior();
            }
        });
    },
    /**
     * If behaviorsData is set, update only those behaviors, if not, recompute
     * every behavior of this.field
     *
     * @param {Array[Object]} behaviorsData
     * @param {Element} [anchor] element to which to inject the behavior
     * @param {string} [type] html class representing the behavior type
     *                        (i.e.: @see o_knowledge_behavior_type_... )
     */
    updateBehaviors: function (behaviorsData = []) {
        if (!behaviorsData.lenth) {
            // no behaviorsData, recreate the array from the field value.
            this._scanFieldForBehaviors(behaviorsData);
        }

        // inject new behaviors
        behaviorsData.forEach(behaviorData => {
            const anchor = behaviorData.anchor;
            const {Behavior} = this.behavior_types[behaviorData.type] || {};
            if (!Behavior) {
                return;
            }
            if (!anchor.oKnowledgeBehavior) {
                anchor.oKnowledgeBehavior = new Behavior(this, anchor, this.mode);
            }
            this.behavior_anchors.add(anchor);
        });
    },
    /**
     * @param {Object}
     * @param {Element} [container] element which has a toolbar anchor
     * @param {Element} [anchor] element in which to inject the toolbar
     * @param {string} [type] html class representing the toolbar type
     *                        (i.e.: @see o_knowledge_toolbar_type_... )
     * @returns {Promise} promise to append this toolbar
     */
    _createToolbar: function ({container, anchor, type}) {
        const {Toolbar, template} = this.toolbar_types[type] || {};
        if (!Toolbar) {
            return;
        }
        const toolbar = new Toolbar(this, container, anchor, template, this.editor, this.component.componentRef.comp.uiService);
        anchor.oKnowledgeToolbar = toolbar;
        this.toolbar_anchors.add(anchor);
        const firstElementChild = anchor.firstElementChild;
        if (firstElementChild) {
            return toolbar.replace(firstElementChild);
        }
        return toolbar.appendTo(anchor);
    },
    /**
     * Clean @see behavior_anchors set when a behavior is removed from the dom
     *
     * @param {Event} event
     */
    _onBehaviorRemoved: function (event) {
        event.stopPropagation();
        this.behavior_anchors.delete(event.data.anchor);
    },
    /**
     * Clean @see toolbar_anchors set when a toolbar is removed from the dom
     *
     * @param {Event} event
     */
    _onToolbarRemoved: function (event) {
        event.stopPropagation();
        this.toolbar_anchors.delete(event.data.anchor);
    },
    /**
     * @param {Event} e
     * @param {Object} data
     * @param {Array} [toolbarsDatas]
     */
    _onRefreshToolbars: function (e, data = {}) {
        if (this.field) {
            this.updateToolbars("toolbarsData" in data ? data.toolbarsData : []);
        }
    },
    /**
     * @param {Event} e
     * @param {Object} data
     * @param {Array} [behaviorsData]
     */
    _onRefreshBehaviors: function (e, data = {}) {
        if (this.field) {
            this.updateBehaviors("behaviorsData" in data ? data.behaviorsData : []);
        }
    },
    /**
     * @param {Event} e
     * @param {Object} data
     * @param {Array} [behaviorsData]
     * @param {Array} [toolbarsDatas]
     */
    _onRefreshInjector: function (e, data = {}) {
        if (this.field) {
            this._onRefreshBehaviors(e, data);
            this._onRefreshToolbars(e, data);
        }
    }
});

export {
    FieldHtmlInjector,
};
