/**
 * @typedef { import("../../../../html_editor/static/src/editor").EditorContext } EditorContext
 * @typedef { any } LoadResult
 * @typedef { any } ActionValue
 * @typedef {{
 *  mainParam: any,
 *  [param: string]: any,
 * }} ActionParams
 * In the XML template, the `actionParam` prop can take 2 kinds of values: an
 * Object or something else (string, array, function...).
 * If `actionParams` takes something that is not a object, it is passed as
 * `mainParam`.
 * If `actionParams` takes an object, each key is forwarded to the parameter.
 * e.g.:
 *     <BuilderButton action="'customAction'" actionParam="{ customKey: 0 }"/>
 * is passed as
 *     `params: { customKey: 0 }`
 *
 * @typedef { Object } NextBuilderAction
 * @property { ActionValue } actionValue
 * @property { ActionParams } actionParam
 *
 * SelectableContext is available on BuilderComponents that make the user choose
 * among a list of items (i.e. BuilderSelect and BuilderButtonGroup).
 * @typedef { Object } SelectableContext
 * @property { Object[] } items
 */

/**
 * @typedef { import("../../../../html_editor/static/src/editor").EditorContext } EditorContext
 */

export class BuilderAction {
    /** @type { string[] } */
    static dependencies = [];
    /**
     * @param { EditorContext } context
     */
    constructor(context) {
        /** @type { EditorContext['document'] } **/
        this.document = context.document;
        this.window = context.document.defaultView;
        /** @type { EditorContext['editable'] } **/
        this.editable = context.editable;
        /** @type { EditorContext['config'] } **/
        this.config = context.config;
        /** @type { EditorContext['services'] } **/
        this.services = context.services;
        /** @type { EditorContext['dependencies'] } **/
        this.dependencies = context.dependencies;
        /** @type { EditorContext['getResource'] } **/
        this.getResource = context.getResource;
        /** @type { EditorContext['dispatchTo'] } **/
        this.dispatchTo = context.dispatchTo;
        /** @type { EditorContext['delegateTo'] } **/
        this.delegateTo = context.delegateTo;

        this.setup();

        // Preview is enabled by default in non-reload actions,
        // and disabled by default in reload actions.
        this.preview ??= this.reload ? false : true;
        this.withLoadingEffect ??= true;
        this.loadOnClean ??= false;
        // canTimeout is enabled when no load is used to avoid staying stuck
        // in the mutex if apply fails silently.
        this.canTimeout ??= !this.has("load");
    }

    /**
     * Called after dependencies and services are assigned.
     * Subclasses override this instead of the constructor.
     */
    setup() {
        // Optional override in subclasses
    }

    /**
     * Prepare some asynchronous call `onWillStart` and `onWillUpdateProps` of
     * the BuilderComponent.
     * A good practice is to use a caching strategy for the data fetched here.
     *
     * @param { Object } context
     * @param { ActionParams } context.actionParam
     * @param { ActionValue } context.actionValue
     */
    async prepare(context) {}

    /**
     * Set a priority to the action in comparison with its sibling components.
     * Used in combination with selectable builder components (i.e.
     * `BuilderButtonGroup` or `BuilderSelect`) to determine which button/select
     * item should be active when several items could qualify. The item with the
     * highest priority is ultimately validated as active.
     *
     * e.g.: `classAction`'s priority is determined by the number of classes
     * that apply. If button A sets no class (priority = 0), button B sets
     * ".some-class" (priority = 1) and button C sets
     * ".some-class.some-other-class" (priority = 2), the active button is the
     * one that has the most classes applied to the editingElement.
     *
     * @param { Object } context
     * @param { ActionParams } context.params
     * @param { ActionValue } context.value
     * @returns { number } default=0
     */
    getPriority(context) {}

    /**
     * Apply the action on the editing element. Can be async.
     * `apply` is called on preview (if preview=true), on apply, and on clean if
     * `clean` is not defined on the action.
     * In cases with an async `apply` and `preview=true`, @see load.
     *
     * @param { Object } context
     * @param { import("./dependency_manager").DependencyManager } context.dependencyManager
     * @param { boolean } context.isPreviewing
     * @param { HTMLElement } context.editingElement
     * @param { ActionValue } context.value
     * @param { ActionParams } [context.params]
     * @param { LoadResult } [context.loadResult]
     * @param { SelectableContext } [context.selectableContext]
     */
    async apply(context) {}

    /**
     * Return the current value of the action on the element.
     * Used in combination with inputs (BuilderTextInput, BuilderNumberInput,
     * BuilderCheckbox, BuilderRange, BuilderDateTimePicker...). For other
     * components, @see isApplied.
     *
     * @param { Object } context
     * @param { HTMLElement } context.editingElement
     * @param { ActionParams } [context.params]
     * @returns { any }
     */
    getValue(context) {}

    /**
     * Whether the action is already applied.
     * Used in combination with builder components that can only be active or
     * not (i.e. not inputs). For inputs, @see getValue.
     *
     * @param { Object } context
     * @param { HTMLElement } context.editingElement
     * @param { ActionValue } context.value
     * @param { ActionParams } [context.params]
     * @returns {boolean}
     */
    isApplied(context) {}

    /**
     * Clean/reset the value if needed. Can be async.
     * If not defined, `apply` will be called instead.
     *
     * @param { Object } context
     * @param { import("./dependency_manager").DependencyManager } context.dependencyManager
     * @param { NextBuilderAction } context.nextAction
     * @param { boolean } context.isPreviewing
     * @param { HTMLElement } context.editingElement
     * @param { ActionValue } context.value
     * @param { ActionParams } [context.params]
     * @param { LoadResult } [context.loadResult]
     * @param { SelectableContext } [context.selectableContext]
     */
    async clean(context) {}

    /**
     * Load and return some data before calling `apply` if needed. The return
     * value is passed as `loadResult` in the `apply` context.
     * /!\ By itself, `load` SHOULD NOT have any effect.
     *
     * Should be used when there is a preview: when triggering an action after
     * another one, the previous call to `apply` is cancelled. But if `apply` is
     * async, the builder has to wait for the end of the call (and clean) before
     * applying the next action. In order to avoid stalling the builder, you can
     * use `load`: the asynchronous code will always run before `apply`, but if
     * the user then triggers another action, we do not wait for `load` to
     * finish and we process the new preview directly.
     *
     * @param { Object } context
     * @param { HTMLElement } context.editingElement
     * @returns { Promise<LoadResult> }
     */
    async load(context) {}

    /**
     * Check if a BuilderAction method has been overridden and should therefore
     * be taken into account.
     *
     * @param { "prepare"|"getPriority"|"load"|"apply"|"clean"|"isApplied"|"getValue" } method
     * @returns { boolean }
     */
    has(method) {
        const baseMethod = BuilderAction.prototype[method];
        const actualMethod = this.constructor.prototype[method];
        return baseMethod !== actualMethod;
    }
}
