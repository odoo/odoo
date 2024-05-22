odoo.define('web_editor.base', function (require) {
'use strict';

// TODO this should be re-removed as soon as possible.

var ajax = require('web.ajax');
var session = require('web.session');

var domReady = new Promise(function(resolve) {
    $(resolve);
});

return {
    /**
     * Retrieves all the CSS rules which match the given parser (Regex).
     *
     * @param {Regex} filter
     * @returns {Object[]} Array of CSS rules descriptions (objects). A rule is
     *          defined by 3 values: 'selector', 'css' and 'names'. 'selector'
     *          is a string which contains the whole selector, 'css' is a string
     *          which contains the css properties and 'names' is an array of the
     *          first captured groups for each selector part. E.g.: if the
     *          filter is set to match .fa-* rules and capture the icon names,
     *          the rule:
     *              '.fa-alias1::before, .fa-alias2::before { hello: world; }'
     *          will be retrieved as
     *              {
     *                  selector: '.fa-alias1::before, .fa-alias2::before',
     *                  css: 'hello: world;',
     *                  names: ['.fa-alias1', '.fa-alias2'],
     *              }
     */
    cacheCssSelectors: {},
    getCssSelectors: function (filter) {
        if (this.cacheCssSelectors[filter]) {
            return this.cacheCssSelectors[filter];
        }
        this.cacheCssSelectors[filter] = [];
        var sheets = document.styleSheets;
        for (var i = 0; i < sheets.length; i++) {
            var rules;
            try {
                // try...catch because Firefox not able to enumerate
                // document.styleSheets[].cssRules[] for cross-domain
                // stylesheets.
                rules = sheets[i].rules || sheets[i].cssRules;
            } catch (e) {
                console.warn("Can't read the css rules of: " + sheets[i].href, e);
                continue;
            }
            if (!rules) {
                continue;
            }

            for (var r = 0 ; r < rules.length ; r++) {
                var selectorText = rules[r].selectorText;
                if (!selectorText) {
                    continue;
                }
                var selectors = selectorText.split(/\s*,\s*/);
                var data = null;
                for (var s = 0; s < selectors.length; s++) {
                    var match = selectors[s].trim().match(filter);
                    if (!match) {
                        continue;
                    }
                    if (!data) {
                        data = {
                            selector: match[0],
                            css: rules[r].cssText.replace(/(^.*\{\s*)|(\s*\}\s*$)/g, ''),
                            names: [match[1]]
                        };
                    } else {
                        data.selector += (', ' + match[0]);
                        data.names.push(match[1]);
                    }
                }
                if (data) {
                    this.cacheCssSelectors[filter].push(data);
                }
            }
        }
        return this.cacheCssSelectors[filter];
    },
    /**
     * List of font icons to load by editor. The icons are displayed in the media
     * editor and identified like font and image (can be colored, spinned, resized
     * with fa classes).
     * To add font, push a new object {base, parser}
     *
     * - base: class who appear on all fonts
     * - parser: regular expression used to select all font in css stylesheets
     *
     * @type Array
     */
    fontIcons: [{base: 'fa', parser: /\.(fa-(?:\w|-)+)::?before/i}],
    /**
     * Searches the fonts described by the @see fontIcons variable.
     */
    computeFonts: _.once(function () {
        var self = this;
        _.each(this.fontIcons, function (data) {
            data.cssData = self.getCssSelectors(data.parser);
            data.alias = _.flatten(_.map(data.cssData, _.property('names')));
        });
    }),
    /**
     * If a widget needs to be instantiated on page loading, it needs to wait
     * for appropriate resources to be loaded. This function returns a Promise
     * which is resolved when the dom is ready, the session is bound
     * (translations loaded) and the XML is loaded. This should however not be
     * necessary anymore as widgets should not be parentless and should then be
     * instantiated (directly or not) by the page main component (webclient,
     * website root, editor bar, ...). The DOM will be ready then, the main
     * component is in charge of waiting for the session and the XML can be
     * lazy loaded thanks to the @see Widget.xmlDependencies key.
     *
     * @returns {Promise}
     */
    ready: function () {
        return Promise.all([domReady, session.is_bound, ajax.loadXML()]);
    },
};
});

//==============================================================================

odoo.define('web_editor.context', function (require) {
'use strict';

// TODO this should be re-removed as soon as possible.

function getContext(context) {
    var html = document.documentElement;
    return _.extend({
        lang: (html.getAttribute('lang') || 'en_US').replace('-', '_'),

        // Unfortunately this is a mention of 'website' in 'web_editor' as there
        // was no other way to do it as this was restored in a stable version.
        // Indeed, the editor is currently using this context at the root of JS
        // module, so there is no way for website to hook itself before
        // web_editor uses it (without a risky refactoring of web_editor in
        // stable). As mentioned above, the editor should not use this context
        // anymore anyway (this was restored by the saas-12.2 editor revert).
        'website_id': html.getAttribute('data-website-id') | 0,
    }, context || {});
}
function getExtraContext(context) {
    var html = document.documentElement;
    return _.extend(getContext(), {
        editable: !!(html.dataset.editable || $('[data-oe-model]').length), // temporary hack, this should be done in python
        translatable: !!html.dataset.translatable,
        edit_translations: !!html.dataset.edit_translations,
    }, context || {});
}

return {
    get: getContext,
    getExtra: getExtraContext,
};
});

//==============================================================================

odoo.define('web_editor.ready', function (require) {
'use strict';

// TODO this should be re-removed as soon as possible.

var base = require('web_editor.base');

return base.ready();
});
