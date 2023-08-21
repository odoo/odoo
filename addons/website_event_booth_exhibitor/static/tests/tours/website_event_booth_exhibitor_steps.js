/** @odoo-module **/

    import Class from "@web/legacy/js/core/class";

    var FinalSteps = Class.extend({

        _getSteps: function () {
            return [{
                trigger: 'h3:contains("Booth Registration completed!")',
                run: function() {},
            }];
        },

    });

    export default FinalSteps;
