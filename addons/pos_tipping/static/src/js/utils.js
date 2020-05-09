odoo.define("pos_restaurant.utils", function(require) {

    var utils = {
        /**
         * This can be used to facilitate a user searching a list of
         * objects. E.g. a user searches through orders and types
         * "John 12". This will return any object that contains both
         * "john" and "12" anywhere in it's values. The search is
         * case-insensitive.
         *
         * @param {Array} array - An array of objects that should be searched
         * @param {String} terms - A space-separated string with search terms
         * @param {Array} [properties] - If supplied limits searching
         * to the specified properties
         */
        full_search: function(array, terms, properties) {
            var matched_searchables = [];
            terms = _.compact(terms.toLowerCase().split(' ')); // compact to remove ''

            array.forEach(function (searchable) {
                var failed_term = false;
                var values_to_search = _.values(searchable);
                if (properties) {
                    values_to_search = _.map(properties, function (prop) {
                        return searchable[prop];
                    });
                }

                for (var i = 0; i < terms.length && !failed_term; i++) {
                    var term = terms[i];
                    failed_term = !_.any(values_to_search, function (value) {
                        return String(value).toLowerCase().indexOf(term) !== -1;
                    });
                }

                if (!failed_term) {
                    matched_searchables.push(searchable);
                }
            });

            return matched_searchables;
        }
    };

    return utils;
});
