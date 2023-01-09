/** @odoo-module **/

const xmlSerializer = new XMLSerializer();
const domParser = new DOMParser();

function traverse(tree, f) {
    if (f(tree)) {
        _.each(tree.children, function (c) {
            traverse(c, f);
        });
    }
}

/**
 * Given the result of a get_views, produces the equivalent of what was previously
 * returned, such that legacy views continue working as before without any adaptations.
 *
 * @param {string} resModel
 * @param {Object} views "views" key of the result of a get_views
 * @param {Object} models maps of model name -> fields_get
 * @returns {Object} similar to what was previously returned by load_views
 */
export function generateLegacyLoadViewsResult(resModel, views, models) {
    const legacyFieldViews = {
        fields: models[resModel],
        fields_views: {},
    };
    if (views.search && views.search.filters) {
        legacyFieldViews.filters = views.search.filters;
    }
    for (const viewType in views) {
        const { arch, toolbar, id } = views[viewType];
        const { arch: processedArch, viewFields } = processArch(arch, viewType, resModel, models);
        legacyFieldViews.fields_views[viewType] = {
            arch: processedArch,
            fields: viewFields,
            model: resModel,
            toolbar,
            view_id: id,
        };
    }
    return legacyFieldViews;
}

/**
 * Given an arch with inline x2many subviews, generates the object of fields
 * appearing in the arch, with a "views" key that contains the descriptions of
 * their subviews (whose archs are removed from the main arch).
 *
 * @param {string} arch
 * @param {string} viewType
 * @param {string} resModel
 * @param {Object} models
 * @returns {Object} the processed arch and the (view) fields description
 */
export function processArch(arch, viewType, resModel, models) {
    const viewFields = {};
    const archDoc = domParser.parseFromString(arch, "text/xml").documentElement;
    traverse(archDoc, function (node) {
        if (node.nodeType === 3) {
            return false;
        }
        if (node.tagName === "field") {
            const fieldName = node.getAttribute("name");
            viewFields[fieldName] = viewFields[fieldName] || {
                ...models[resModel][fieldName],
                string: node.getAttribute("string") || models[resModel][fieldName].string,
                views: {},
            };
            // extract subviews
            // note: this should only be done for form views, because x2many subviews doesn't make
            // any sense in any other view type, but sometimes in the codebase, people inline
            // subviews in list views (e.g. sale.order.form.inherit.sale.product.configurator) so
            // we remove them from the main arch anyway, to mock the previous behavior
            if (viewType === "form" || viewType === "list") {
                const coModel = models[resModel][fieldName].relation;
                const views = {};
                for (const childNode of [...node.children]) {
                    const viewType = childNode.tagName === "tree" ? "list" : childNode.tagName;
                    const { arch: subViewArch, viewFields: subViewFields } = processArch(
                        xmlSerializer.serializeToString(childNode),
                        viewType,
                        coModel,
                        models
                    );
                    views[viewType] = { arch: subViewArch, fields: subViewFields };
                    node.removeChild(childNode);
                }
                viewFields[fieldName].views = views;
            }
            return false;
        }
        // list: extract groupby informations
        if (viewType === "list" && node.tagName === "groupby" && node !== archDoc) {
            const fieldName = node.getAttribute("name");
            const coModel = models[resModel][fieldName].relation;
            const { arch: subViewArch, viewFields: subViewFields } = processArch(
                xmlSerializer.serializeToString(node),
                "groupby",
                coModel,
                models
            );
            const groupbyView = { arch: subViewArch, fields: subViewFields };
            viewFields[fieldName] = viewFields[fieldName] || {
                ...models[resModel][fieldName],
                views: {},
            };
            viewFields[fieldName].views.groupby = groupbyView;
            for (const child of [...node.children]) {
                node.removeChild(child);
            }
            return false;
        }
        return true;
    });
    return { arch: xmlSerializer.serializeToString(archDoc), viewFields };
}
