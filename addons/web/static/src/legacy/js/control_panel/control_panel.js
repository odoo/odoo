/** @odoo-module alias=web.ControlPanel **/
    
    import ActionMenus from "web.ActionMenus";
    import Pager from "web.Pager";
    import { LegacyComponent } from "@web/legacy/legacy_component";
    import { sprintf } from "@web/core/utils/strings";

    const {
        onMounted,
        onPatched,
        onWillDestroy,
        onWillUpdateProps,
        toRaw,
        useRef,
        useSubEnv,
    } = owl;

    /**
     * TODO: remove this whole mechanism as soon as `cp_content` is completely removed.
     * Extract the 'cp_content' key of the given props and return them as well as
     * the extracted content.
     * @param {Object} props
     * @returns {Object}
     */
    function getAdditionalContent(props) {
        const additionalContent = {};
        if ('cp_content' in props) {
            const content = props.cp_content || {};
            if ('$buttons' in content) {
                additionalContent.buttons = content.$buttons;
            }
            if ('$searchview' in content) {
                additionalContent.searchView = content.$searchview;
            }
            if ('$pager' in content) {
                additionalContent.pager = content.$pager;
            }
            if ('$searchview_buttons' in content) {
                additionalContent.searchViewButtons = content.$searchview_buttons;
            }
        }
        return additionalContent;
    }

    /**
     * Control panel
     *
     * The control panel of the action|view. In its standard form, it is composed of
     * several sections/subcomponents.
     *
     * Note: an additional temporary (and ugly) mechanic allows to inject a jQuery element
     * given in `props.cp_content` in a related section:
     *      $buttons -> [Buttons]
     *      $searchview -> [Search View]
     *      $searchview_buttons -> [Search Menus]
     *      $pager -> [Pager]
     * This system must be replaced by proper slot usage and the static template
     * inheritance mechanism when converting the views/actions.
     * @extends Component
     */
    class ControlPanel extends LegacyComponent {
        setup() {
            this.additionalContent = getAdditionalContent(this.props);

            let subEnvView = this.props.view;
            useSubEnv({
                action: this.props.action,
                get view() {
                    return subEnvView;
                },
            });

            // Reference hooks
            this.contentRefs = {
                buttons: useRef('buttons'),
                pager: useRef('pager'),
                searchView: useRef('searchView'),
                searchViewButtons: useRef('searchViewButtons'),
            };

            this.fields = this._formatFields(toRaw(this.props.fields || {}));

            this.sprintf = sprintf;

            onWillDestroy(() => {
                const content = this.props.cp_content;
                if (content) {
                    if (content.$buttons) {
                        content.$buttons.remove();
                    }
                    if (content.$searchview) {
                        content.$searchview.remove();
                    }
                    if (content.$pager) {
                        content.$pager.remove();
                    }
                    if (content.$searchview_buttons) {
                        content.$searchview_buttons.remove();
                    }
                }
            });

            // Cannot use useEffect. See prepareForFinish in owl_compatibility.js
            onMounted(() => this._attachAdditionalContent());
            onPatched(() => this._attachAdditionalContent());
            onWillUpdateProps((nextProps) => {
                // Note: action and searchModel are not likely to change during
                // the lifespan of a ControlPanel instance, so we only need to update
                // the view information.
                if ("view" in nextProps) {
                    subEnvView = nextProps.view;
                }
                if ("fields" in nextProps) {
                    this.fields = this._formatFields(toRaw(nextProps.fields));
                }
                this.additionalContent = getAdditionalContent(nextProps);
            });
        }

        //---------------------------------------------------------------------
        // Private
        //---------------------------------------------------------------------

        /**
         * Attach additional content extracted from the props 'cp_content' key, if any.
         * @private
         */
        _attachAdditionalContent() {
            for (const key in this.additionalContent) {
                if (this.additionalContent[key] && this.additionalContent[key].length) {
                    const target = this.contentRefs[key].el;
                    if (target) {
                        target.innerHTML = "";
                        target.append(...this.additionalContent[key]);
                    }
                }
            }
        }

        /**
         * Give `name` and `description` keys to the fields given to the control
         * panel.
         * @private
         * @param {Object} fields
         * @returns {Object}
         */
        _formatFields(fields) {
            const formattedFields = {};
            for (const fieldName in fields) {
                formattedFields[fieldName] = Object.assign({
                    description: fields[fieldName].string,
                    name: fieldName,
                }, fields[fieldName]);
            }
            return formattedFields;
        }
    }
    ControlPanel.components = {
        ActionMenus, Pager,
    };
    ControlPanel.defaultProps = {
        breadcrumbs: [],
        fields: {},
        views: [],
        withBreadcrumbs: true,
    };
    ControlPanel.props = {
        action: Object,
        breadcrumbs: { type: Array, optional: true },
        cp_content: { type: Object, optional: 1 },
        fields: { type: Object, optional: true },
        pager: { validate: p => typeof p === 'object' || p === null, optional: 1 },
        actionMenus: { validate: s => typeof s === 'object' || s === null, optional: 1 },
        title: { type: String, optional: 1 },
        view: { type: Object, optional: 1 },
        views: { type: Array, optional: true },
        withBreadcrumbs: { type: Boolean, optional: true },
    };
    ControlPanel.template = 'web.Legacy.ControlPanel';

    export default ControlPanel;
