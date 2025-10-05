/** @odoo-module **/

class FinalSteps {

    _getSteps() {
        return [{
            trigger: 'h4:contains("Booth Registration completed!")',
        }];
    }

}

export default FinalSteps;
