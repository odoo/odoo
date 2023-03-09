/** @odoo-module alias=web.AbstractModel **/

/**
 * An AbstractModel is the M in MVC.  We tend to think of MVC more on the server
 * side, but we are talking here on the web client side.
 *
 * The duties of the Model are to fetch all relevant data, and to make them
 * available for the rest of the view.  Also, every modification to that data
 * should pass through the model.
 *
 * Note that the model is not a widget, it does not need to be rendered or
 * appended to the dom.  However, it inherits from the EventDispatcherMixin,
 * in order to be able to notify its parent by bubbling events up.
 *
 * The model is able to generate sample (fake) data when there is no actual data
 * in database.  This feature can be activated by instantiating the model with
 * param "useSampleModel" set to true.  In this case, the model instantiates a
 * duplicated version of itself, parametrized to call a SampleServer (JS)
 * instead of doing RPCs.  Here is how it works: the main model first load the
 * data normally (from database), and then checks whether the result is empty or
 * not.  If it is, it asks the sample model to load with the exact same params,
 * and it thus enters in "sample" mode.  The model keeps doing this at reload,
 * but only if the (re)load params haven't changed: as soon as a param changes,
 * the "sample" mode is left, and it never enters it again in the future (in the
 * lifetime of the model instance).  To access those sample data from the outside,
 * 'get' must be called with the option "withSampleData" set to true.  In
 * this case, if the main model is in "sample" mode, it redirects the call to the
 * sample model.
 */

import fieldUtils from 'web.field_utils';
import mvc from 'web.mvc';


var AbstractModel = mvc.Model.extend({

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @param {any} _
     * @param {Object} [options]
     */
    get(_, options) {
        return this.__get(...arguments);
    },
    /**
     * @override
     */
    load(params) {
        this.loadParams = params;
        return this.__load(...arguments);
    },
    /**
     * When something changes, the data may need to be refetched.  This is the
     * job for this method: reloading (only if necessary) all the data and
     * making sure that they are ready to be redisplayed.
     *
     * @param {any} _
     * @param {Object} [params]
     * @returns {Promise}
     */
    async reload(_, params) {
        return this.__reload(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {Object}
     */
    __get() {
        return {};
    },
    /**
     * To override to do the initial load of the data (this function is supposed
     * to be called only once).
     *
     * @private
     * @returns {Promise}
     */
    async __load() {
        return Promise.resolve();
    },
    /**
     * Processes date(time) and selection field values sent by the server.
     * Converts data(time) values to moment instances.
     * Converts false values of selection fields to 0 if 0 is a valid key,
     * because the server doesn't make a distinction between false and 0, and
     * always sends false when value is 0.
     *
     * @param {Object} field the field description
     * @param {*} value
     * @returns {*} the processed value
     */
    _parseServerValue: function (field, value) {
        if (field.type === 'date' || field.type === 'datetime') {
            // process date(time): convert into a moment instance
            value = fieldUtils.parse[field.type](value, field, {isUTC: true});
        } else if (field.type === 'selection' && value === false) {
            // process selection: convert false to 0, if 0 is a valid key
            var hasKey0 = _.find(field.selection, function (option) {
                return option[0] === 0;
            });
            value = hasKey0 ? 0 : value;
        }
        return value;
    },
    /**
     * To override to reload data (this function may be called several times,
     * after the initial load has been done).
     *
     * @private
     * @returns {Promise}
     */
    async __reload() {
        return Promise.resolve();
    },
});

export default AbstractModel;
