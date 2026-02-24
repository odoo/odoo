$.JST.loadDecorator("RESOURCE_ROW", function(resTr, res) {
    console.log('RESOURCE_ROW-------------------------')
    resTr.find(".delRes").click(function(){$(this).closest("tr").remove()});
});



$.JST.loadDecorator("ASSIGNMENT_ROW", function(assigTr, taskAssig) {
    console.log('ASSIGNMENT_ROW-------------------------')
    var resEl = assigTr.find("[name=resourceId]");
    var opt = $("<option>");
    resEl.append(opt);

    for(var i=0; i<taskAssig.task.master.resources.length; i++) {
        var res = taskAssig.task.master.resources[i];
        opt = $("<option>");
        opt.val(res.id).html(res.name);
        if(taskAssig.assig.resourceId == res.id)
            opt.attr("selected", "true");
        resEl.append(opt);
    }

    var roleEl = assigTr.find("[name=roleId]");
    for(var i=0; i<taskAssig.task.master.roles.length; i++) {
        var role = taskAssig.task.master.roles[i];
        var optr = $("<option>");
        optr.val(role.id).html(role.name);
        if(taskAssig.assig.roleId == role.id)
            optr.attr("selected", "true");
        roleEl.append(optr);
    }

    if(taskAssig.task.master.permissions.canWrite && taskAssig.task.canWrite) {
        assigTr.find(".delAssig").click(function() {
            var tr = $(this).closest("[assId]").fadeOut(200, function(){$(this).remove()});
        });
    }
});



function loadI18n() {

    GanttMaster.messages = {
        "CANNOT_WRITE":"No permission to change the following task:",
        "CHANGE_OUT_OF_SCOPE":"Project update not possible as you lack rights for updating a parent project.",
        "START_IS_MILESTONE":"Start date is a milestone.",
        "END_IS_MILESTONE":"End date is a milestone.",
        "TASK_HAS_CONSTRAINTS":"Task has constraints.",
        "GANTT_ERROR_DEPENDS_ON_OPEN_TASK":"Error: there is a dependency on an open task.",
        "GANTT_ERROR_DESCENDANT_OF_CLOSED_TASK":"Error: due to a descendant of a closed task.",
        "TASK_HAS_EXTERNAL_DEPS":"This task has external dependencies.",
        "GANNT_ERROR_LOADING_DATA_TASK_REMOVED":"GANNT_ERROR_LOADING_DATA_TASK_REMOVED",
        "CIRCULAR_REFERENCE":"Circular reference.",
        "CANNOT_DEPENDS_ON_ANCESTORS":"Cannot depend on ancestors.",
        "INVALID_DATE_FORMAT":"The data inserted are invalid for the field format.",
        "GANTT_ERROR_LOADING_DATA_TASK_REMOVED":"An error has occurred while loading the data. A task has been trashed.",
        "CANNOT_CLOSE_TASK_IF_OPEN_ISSUE":"Cannot close a task with open issues",
        "TASK_MOVE_INCONSISTENT_LEVEL":"You cannot exchange tasks of different depth.",
        "GANTT_QUARTER_SHORT":"Quarter",
        "GANTT_SEMESTER_SHORT":"Sem",
        "CANNOT_MOVE_TASK":"CANNOT_MOVE_TASK",
        "PLEASE_SAVE_PROJECT":"PLEASE_SAVE_PROJECT"
    };
}



function createNewResource(el) {
    var row = el.closest("tr[taskid]");
    var name = row.find("[name=resourceId_txt]").val();
    var url = contextPath + "/applications/teamwork/resource/resourceNew.jsp?CM=ADD&name=" + encodeURI(name);

    openBlackPopup(url, 700, 320, function (response) {
        //fillare lo smart combo
        if (response && response.resId && response.resName) {
            //fillare lo smart combo e chiudere l'editor
            row.find("[name=resourceId]").val(response.resId);
            row.find("[name=resourceId_txt]").val(response.resName).focus().blur();
        }

    });

}

