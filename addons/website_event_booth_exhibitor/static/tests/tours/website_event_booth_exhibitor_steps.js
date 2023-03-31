/** @odoo-module alias=website_event_booth_exhibitor.tour_steps **/
    
    import core from "web.core";

    var FinalSteps = core.Class.extend({

        _getSteps: function () {
            return [{
                trigger: 'h3:contains("Booth Registration completed!")',
                run: function() {},
            }];
        },

    });

    export default FinalSteps;
