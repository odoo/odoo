/* eslint-env node */
exports.aceEditEvent = function(hook, call, editorInfo, rep, documentAttributeManager){

    call.editorInfo.ace_focus = focus;
    function focus(){
        // Simple hook to disable the focus on the pad
    }

};
