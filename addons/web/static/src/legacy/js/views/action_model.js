/** @odoo-module alias=web.ActionModel **/

    import Domain from "web.Domain";
    import { FACET_ICONS } from "web.searchUtils";
    import { Model } from "web.Model";
    import { parseArch } from "web.viewUtils";
    import pyUtils from "web.py_utils";
    import Registry from "web.Registry";

    const isNotNull = (value) => value !== null && value !== undefined;
    const isObject = (obj) => typeof obj === "object" && obj !== null;

    /**
     * @extends Model.Extension
     */
    class ActionModelExtension extends Model.Extension {

        //---------------------------------------------------------------------
        // Public
        //---------------------------------------------------------------------

        /**
         * Initiates the asynchronous tasks of the extension and returns a
         * promise resolved as soon as all the informations necessary to build
         * the search query are ready.
         * @returns {Promise}
         */
        async callLoad() {
            this.loadPromise = super.callLoad(...arguments);
            await this.loadPromise;
        }

        /**
         * Returns a promise resolved when the extension is completely ready.
         * @returns {Promise}
         */
        async isReady() {
            await this.loadPromise;
        }

        //---------------------------------------------------------------------
        // Static
        //---------------------------------------------------------------------

        /**
         * @abstract
         * @param {Object} archs
         * @param {string | null} [viewType=null]
         * @returns {null}
         */
        static extractArchInfo() {
            return null;
        }
    }

    /**
     * @extends Model
     */
    class ActionModel extends Model {

        //---------------------------------------------------------------------
        // Public
        //---------------------------------------------------------------------

        /**
         * @override
         */
        get(property) {
            switch (property) {
                case "query": return this.config.searchQuery || this._getQuery();
                case "facets": return this._getFacets();
            }
            return super.get(...arguments);
        }

        /**
         * Returns a promise resolved when all extensions are completely ready.
         * @returns {Promise}
         */
        async isReady() {
            await this._awaitExtensions();
        }

        //---------------------------------------------------------------------
        // Private
        //---------------------------------------------------------------------

        /**
         * @private
         * @returns {Promise}
         */
        async _awaitExtensions() {
            await Promise.all(this.extensions.flat().map(
                (extension) => extension.isReady()
            ));
        }

        /**
         * @override
         */
        __get(excluded, property) {
            const results = super.__get(...arguments);
            switch (property) {
                case "domain": return [this.config.domain, ...results];
                case "context": return [this.config.context, ...results];
            }
            return results;
        }

        /**
         * Validates and formats all facets given by the extensions. This is
         * done here rather than in the search bar because the searchMenuTypes
         * are available only to the model.
         * @private
         * @returns {Object[]}
         */
        _getFacets() {
            const types = this.config.searchMenuTypes || [];
            const isValidType = (type) => (
                !['groupBy', 'comparison'].includes(type) || types.includes(type)
            );
            const facets = [];
            for (const extension of this.extensions.flat()) {
                for (const facet of extension.get("facets") || []) {
                    if (!isValidType(facet.type)) {
                        continue;
                    }
                    facet.separator = facet.type === 'groupBy' ? ">" : this.env._t("or");
                    if (facet.type in FACET_ICONS) {
                        facet.icon = FACET_ICONS[facet.type];
                    }
                    facets.push(facet);
                }
            }
            return facets;
        }

        /**
         * @typedef TimeRanges
         * @property {string} fieldName
         * @property {string} comparisonRangeId
         * @property {Array[]} range
         * @property {string} rangeDescription
         * @property {Array[]} comparisonRange
         * @property {string} comparisonRangeDescription
         */
        /**
         * @typedef Query
         * @property {Object} context
         * @property {Array[]} domain
         * @property {string[]} groupBy
         * @property {string[]} orderedBy
         * @property {TimeRanges?} timeRanges
         */
        /**
         * @private
         * @returns {Query}
         */
        _getQuery() {
            const evalContext = this.env.session.user_context;
            const contexts = this.__get(null, "context");
            const domains = this.__get(null, "domain");
            const query = {
                context: pyUtils.eval("contexts", contexts, evalContext),
                domain: Domain.prototype.normalizeArray(
                    pyUtils.eval("domains", domains, evalContext)
                ),
                orderedBy: this.get("orderedBy") || [],
            };
            const searchMenuTypes = this.config.searchMenuTypes || [];
            if (searchMenuTypes.includes("groupBy")) {
                query.groupBy = this.get("groupBy") || [];
            } else {
                query.groupBy = [];
            }
            if (searchMenuTypes.includes("comparison")) {
                query.timeRanges = this.get("timeRanges") || {};
            }
            return query;
        }

        /**
         * Overridden to trigger a "search" event as soon as the query data
         * are ready.
         * @override
         */
        async _loadExtensions({ isInitialLoad }) {
            await super._loadExtensions(...arguments);
            if (!isInitialLoad) {
                this.trigger("search", this.get("query"));
                await this._awaitExtensions();
            }
        }

        //---------------------------------------------------------------------
        // Static
        //---------------------------------------------------------------------

        /**
         * @param {Object} archs
         * @param {string | null} [viewType=null]
         * @returns {Object}
         */
        static extractArchInfo(archs, viewType = null) {
            const parsedArchs = {};
            if (!archs.search) {
                archs.search = "<search/>";
            }
            for (const key in archs) {
                const { attrs, children } = parseArch(archs[key]);
                const objectChildren = children.filter(isObject);
                parsedArchs[key] = {
                    attrs,
                    children: objectChildren,
                };
            }
            const archInfo = {};
            for (const key of this.registry.keys()) {
                const extension = this.registry.get(key);
                const result = extension.extractArchInfo(parsedArchs, viewType);
                if (isNotNull(result)) {
                    archInfo[key] = result;
                }
            }
            return archInfo;
        }
    }

    ActionModel.Extension = ActionModelExtension;
    ActionModel.registry = new Registry(null,
        (value) => value.prototype instanceof ActionModel.Extension
    );

    export default ActionModel;
