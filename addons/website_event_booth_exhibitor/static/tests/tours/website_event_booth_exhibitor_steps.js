/** @odoo-module **/

class FinalSteps {

    _getSteps() {
        return [{
            trigger: 'h3:contains("Booth Registration completed!")',
            run: function() {},
        }];
    }

}

export default FinalSteps;
