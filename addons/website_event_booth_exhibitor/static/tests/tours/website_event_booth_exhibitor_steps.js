class FinalSteps {

    _getSteps() {
        return [{
            content: "Click on confirm button",
            trigger: "button.o_wbooth_registration_confirm",
            run: "click",
        }, {
            trigger: 'h4:contains("Booth Registration completed!")',
        }];
    }

}

export default FinalSteps;
