/*
 Copyright (c) 2012-2017 Open Lab
 Written by Roberto Bicchierai and Silvia Chelazzi http://roberto.open-lab.com
 Permission is hereby granted, free of charge, to any person obtaining
 a copy of this software and associated documentation files (the
 "Software"), to deal in the Software without restriction, including
 without limitation the rights to use, copy, modify, merge, publish,
 distribute, sublicense, and/or sell copies of the Software, and to
 permit persons to whom the Software is furnished to do so, subject to
 the following conditions:

 The above copyright notice and this permission notice shall be
 included in all copies or substantial portions of the Software.

 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
 LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
 OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
 WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */
function GridEditor(master) {
  this.master = master; // is the a GantEditor instance

  var editorTabel = $.JST.createFromTemplate({}, "TASKSEDITHEAD");
  if (!master.permissions.canSeeDep)
    editorTabel.find(".requireCanSeeDep").hide();

  this.gridified = $.gridify(editorTabel);

  this.element = this.gridified.find(".gdfTable").eq(1);
}


GridEditor.prototype.fillEmptyLines = function () {
  //console.debug("fillEmptyLines")
  var factory = new TaskFactory();
  var master = this.master;

  //console.debug("GridEditor.fillEmptyLines");
  var rowsToAdd = master.minRowsInEditor - this.element.find(".taskEditRow").length;
  var empty=this.element.find(".emptyRow").length;
  rowsToAdd=Math.max(rowsToAdd,empty>5?0:5-empty);

  //fill with empty lines
  for (var i = 0; i < rowsToAdd; i++) {
    var emptyRow = $.JST.createFromTemplate({}, "TASKEMPTYROW");
    if (!master.permissions.canSeeDep)
      emptyRow.find(".requireCanSeeDep").hide();

    //click on empty row create a task and fill above
    emptyRow.click(function (ev) {
      //console.debug("emptyRow.click")
      var emptyRow = $(this);
      //add on the first empty row only
      if (!master.permissions.canWrite || !master.permissions.canAdd || emptyRow.prevAll(".emptyRow").length > 0)
        return;

      master.beginTransaction();
      var lastTask;
      var start = new Date().getTime();
      var level = 0;
      if (master.tasks[0]) {
        start = master.tasks[0].start;
        level = master.tasks[0].level + 1;
      }

      //fill all empty previouses
      var cnt=0;
      emptyRow.prevAll(".emptyRow").addBack().each(function () {
        cnt++;
        var ch = factory.build("tmp_fk" + new Date().getTime()+"_"+cnt, "", "", level, start, 1);
        console.log('callingggggggggggggg22222222222222 addTask funstion-----------')
        var task = master.addTask(ch);
        lastTask = ch;
      });
      master.endTransaction();
      if (lastTask.rowElement) {
        //lastTask.rowElement.click();  removed R&S 22/03/2016 il click è bindato comunque
        lastTask.rowElement.find("[name=name]").focus();//focus to "name" input
      }
    });
    this.element.append(emptyRow);
  }
};


GridEditor.prototype.addTask = function (task, row, hideIfParentCollapsed) {
  //console.debug("GridEditor.addTask",task,row);
  //var prof = new Profiler("editorAddTaskHtml");

  //remove extisting row
  this.element.find("[taskId=" + task.id + "]").remove();

  var taskRow = $.JST.createFromTemplate(task, "TASKROW");

  if (!this.master.permissions.canSeeDep)
    taskRow.find(".requireCanSeeDep").hide();

  if (!this.master.permissions.canSeePopEdit)
    taskRow.find(".edit .teamworkIcon").hide();

  //save row element on task
  task.rowElement = taskRow;
  this.bindRowEvents(task, taskRow);
console.log('\n\n\nthis-----------',this)
  if (typeof(row) != "number") {
    var emptyRow = this.element.find(".emptyRow:first"); //tries to fill an empty row
    if (emptyRow.length > 0)
      emptyRow.replaceWith(taskRow);
    else
      this.element.append(taskRow);
  } else {
    var tr = this.element.find("tr.taskEditRow").eq(row);
    if (tr.length > 0) {
      tr.before(taskRow);
    } else {
      this.element.append(taskRow);
    }

  }

  //[expand]
  if (hideIfParentCollapsed) {
    if (task.collapsed) taskRow.addClass('collapsed');
    var collapsedDescendant = this.master.getCollapsedDescendant();
    if (collapsedDescendant.indexOf(task) >= 0) taskRow.hide();
  }

  return taskRow;
};

GridEditor.prototype.refreshExpandStatus = function (task) {
  //console.debug("refreshExpandStatus",task);
  if (!task) return;
  if (task.isParent()) {
    task.rowElement.addClass("isParent");
  } else {
    task.rowElement.removeClass("isParent");
  }

  var par = task.getParent();
  if (par && !par.rowElement.is("isParent")) {
    par.rowElement.addClass("isParent");
  }
};
//taskRow.find("#rowExpand").click(function(){
//		var el = $(this);
//		var taskId = el.closest("[taskId]").attr("taskId");
//		var task = self.master.getTask(taskId);
//		task.rowElement.css('display', 'table-row');
//		var descs = task.getDescendant();
//		if (el.is(".exp"))
//		{
//		for (var i = 0; i < descs.length; i++) { 
//		descs[i].rowElement.show();
//		descs[i].rowElement.css('display', 'table-row');
//		descs[i].rowElement.find("#rowExpand").removeClass('exp');
//		if (descs[i].getChildren().length > 0){
//		descs[i].rowElement.find("#txtExpand").text('[');
//		}
//		}
//		self.master.redrawExpand();
//		el.removeclass('exp');
//		el.find "(#txtEx-and)".text('[');
//		}
//		else{
//		for (var i = 0; i < descs.length; i++) 
//		{ 
//		descs[i].rowElement.hide();
//		}
//		self.master.redrawExpand();
//		el.addclass('exp');
//		el.find("#txtExpand").text('}');
//		}
//
//		var visibleTasksId=[];
//		$("table#ganttTable tbody tr").filter(':visible').each(function(){
//			console.log('ganttTable-----------')
//		var id = $(this).closest("[taskId]").attr("taskId");
//		if (id != null)
//		visibleTasksId.push(id);
//		});
//		if (visibleTasksId.length == self.master.tasks.length){
//		self.master.tasks[0].rowElement.find("#txtExpand").text('[');
//		self.master.tasks[0].rowElement.find("#rowExpand").removeClass('exp');
//		}
//		else
//			{
//		self.master.tasks[0].rowElement.find("#txtExpand").text('}');
//		self.master.tasks[0].rowElement.find("#rowExpand").addClass('exp');
//		}
//		});	
		
GridEditor.prototype.refreshTaskRow = function (task) {
	
  var row = task.rowElement;
  
  //////////////////
//  var child = task.getDescendant().length;
//  console.log('child-----------',child)
//  if (task.level == 0){
//	  console.log('rowExpand hiding-----------',task.level)
//  row.find("#rowExpand").hide();
//  }
//  if (child > 0){
//	  console.log('child is greter than zero-----------',child)
//  row.find("#txtExpand").css("padding-left", 4);
//  row.find("#rowExpand").show();
//  }
//  else{
//	  console.log('else-------------')
//  row.find("#rowExpand").hide();  
//	  }
  ///////////////
  

  row.find(".taskRowIndex").html(task.getRow() + 1);
  row.find(".indentCell").css("padding-left", task.level * 10 + 18);
  row.find("[name=name]").val(task.name);
  row.find("[name=code]").val(task.code);
  row.find("[status]").attr("status", task.status);
  row.find("[name=duration]").val(task.duration);
  row.find("[name=progress]").val(task.progress).prop("readonly",task.progressByWorklog==true);
  row.find("[name=startIsMilestone]").prop("checked", task.startIsMilestone);
  row.find("[name=start]").val(new Date(task.start).format()).updateOldValue().prop("readonly",task.depends || !task.canWrite  && !this.master.permissions.canWrite ); // called on dates only because for other field is called on focus event
  row.find("[name=endIsMilestone]").prop("checked", task.endIsMilestone);
  row.find("[name=end]").val(new Date(task.end).format()).updateOldValue();
  row.find("[name=depends]").val(task.depends);
  row.find(".taskAssigs").html(task.getAssigsString());
  console.log('ppc task--------------',task)
	console.log('ppc task.rowElement--------------',task.rowElement)
	console.log('ppc row--------------',row)
//	console.log('ppc task--------------',task)
//	console.log('ppc task--------------',task)
//	console.log('ppc task--------------',task)
//	console.log('ppc task--------------',task)
//	console.log('ppc task--------------',task)
//	console.log('ppc task--------------',task)
  //manage collapsed
  if (task.collapsed)
    row.addClass("collapsed");
  else
    row.removeClass("collapsed");


  //Enhancing the function to perform own operations
  this.master.element.trigger('gantt.task.afterupdate.event', task);
  //profiler.stop();
};

GridEditor.prototype.redraw = function () {
  //console.debug("GridEditor.prototype.redraw")
  for (var i = 0; i < this.master.tasks.length; i++) {
    this.refreshTaskRow(this.master.tasks[i]);
  }
  // check if new emty rows are needed
  if (this.master.fillWithEmptyLines)
    this.fillEmptyLines();

};

GridEditor.prototype.reset = function () {
  this.element.find("[taskid]").remove();
};


GridEditor.prototype.bindRowEvents = function (task, taskRow) {
  var self = this;
  //console.debug("bindRowEvents",this,this.master,this.master.permissions.canWrite, task.canWrite);
  if (this.master.permissions.canWrite && task.canWrite) {
    self.bindRowInputEvents(task, taskRow);

  } else { //cannot write: disable input
    taskRow.find("input").prop("readonly", true);
    taskRow.find("input:checkbox,select").prop("disabled", true);
  }

  if (!this.master.permissions.canSeeDep)
    taskRow.find("[name=depends]").attr("readonly", true);

  self.bindRowExpandEvents(task, taskRow);
  if (this.master.permissions.canSeePopEdit) {
    taskRow.find(".edit").click(function () {self.openFullEditor(task, taskRow, false)});
    taskRow.find(".taskAssigs").dblclick(function () {self.openFullEditor(task, taskRow, true)});
  }
};


GridEditor.prototype.bindRowExpandEvents = function (task, taskRow) {
	  var self = this;
	  //expand collapse
	  taskRow.find(".exp-controller").click(function () {
	    var el = $(this);
	    var taskId = el.closest("[taskid]").attr("taskid");
	    var task = self.master.getTask(taskId);
	    if (task.collapsed) {
	    	console.log('task expanded-----===========-----------------------',task)
	      self.master.expand(task,false);
	    } else {
	    	console.log('task collapsed-----===========-----------------------',self.master)
	      self.master.collapse(task,false);
	    }
	  });
	};

GridEditor.prototype.bindRowInputEvents = function (task, taskRow) {
  var self = this;

  //bind dateField on dates
  taskRow.find(".date").each(function () {
    var el = $(this);
    el.click(function () {
      var inp = $(this);
      inp.dateField({
        inputField: el,
        callback:   function (d) {
          $(this).blur();
        }
      });
    });

    el.blur(function (date) {
      var inp = $(this);
      if (inp.isValueChanged()) {
        if (!Date.isValid(inp.val())) {
          alert(GanttMaster.messages["INVALID_DATE_FORMAT"]);
          inp.val(inp.getOldValue());

        } else {
          var row = inp.closest("tr");
          var taskId = row.attr("taskId");
          var task = self.master.getTask(taskId);

          var leavingField = inp.prop("name");
          var dates = resynchDates(inp, row.find("[name=start]"), row.find("[name=startIsMilestone]"), row.find("[name=duration]"), row.find("[name=end]"), row.find("[name=endIsMilestone]"));
          //console.debug("resynchDates",new Date(dates.start), new Date(dates.end),dates.duration)
          //update task from editor
          self.master.beginTransaction();
          self.master.changeTaskDates(task, dates.start, dates.end);
          self.master.endTransaction();
          inp.updateOldValue(); //in order to avoid multiple call if nothing changed
        }
      }
    });
  });


  //milestones checkbox
  taskRow.find(":checkbox").click(function () {
    var el = $(this);
    var row = el.closest("tr");
    var taskId = row.attr("taskId");

    var task = self.master.getTask(taskId);

    //update task from editor
    var field = el.prop("name");

    if (field == "startIsMilestone" || field == "endIsMilestone") {
      self.master.beginTransaction();
      //milestones
      task[field] = el.prop("checked");
      resynchDates(el, row.find("[name=start]"), row.find("[name=startIsMilestone]"), row.find("[name=duration]"), row.find("[name=end]"), row.find("[name=endIsMilestone]"));
      self.master.endTransaction();
    }

  });


  //binding on blur for task update (date exluded as click on calendar blur and then focus, so will always return false, its called refreshing the task row)
  taskRow.find("input:text:not(.date)").focus(function () {
    $(this).updateOldValue();

  }).blur(function (event) {
    var el = $(this);
    var row = el.closest("tr");
    var taskId = row.attr("taskId");
    var task = self.master.getTask(taskId);
    //update task from editor
    var field = el.prop("name");
    //console.debug("blur",field)

    if (el.isValueChanged()) {
      self.master.beginTransaction();

      if (field == "depends") {

        var oldDeps = task.depends;
        task.depends = el.val();


        // update links
        var linkOK = self.master.updateLinks(task);
        if (linkOK) {
          //synchronize status from superiors states
          var sups = task.getSuperiors();


/*
          for (var i = 0; i < sups.length; i++) {
            if (!sups[i].from.synchronizeStatus())
              break;
          }
*/

          var oneFailed=false;
          var oneUndefined=false;
          var oneActive=false;
          var oneSuspended=false;
          for (var i = 0; i < sups.length; i++) {
            oneFailed=oneFailed|| sups[i].from.status=="STATUS_FAILED";
            oneUndefined=oneUndefined|| sups[i].from.status=="STATUS_UNDEFINED";
            oneActive=oneActive|| sups[i].from.status=="STATUS_ACTIVE";
            oneSuspended=oneSuspended|| sups[i].from.status=="STATUS_SUSPENDED";
          }

          if (oneFailed){
            task.changeStatus("STATUS_FAILED")
          } else if (oneUndefined){
            task.changeStatus("STATUS_UNDEFINED")
          } else if (oneActive){
            task.changeStatus("STATUS_SUSPENDED")
          } else  if (oneSuspended){
            task.changeStatus("STATUS_SUSPENDED")
          } else {
            task.changeStatus("STATUS_ACTIVE")
          }


          self.master.changeTaskDeps(task); //dates recomputation from dependencies
        }

      } else if (field == "duration") {
        var dates = resynchDates(el, row.find("[name=start]"), row.find("[name=startIsMilestone]"), row.find("[name=duration]"), row.find("[name=end]"), row.find("[name=endIsMilestone]"));
        self.master.changeTaskDates(task, dates.start, dates.end);

      } else if (field == "name" && el.val() == "") { // remove unfilled task
        task.deleteTask();
        self.master.gantt.synchHighlight();


      } else if (field == "progress" ) {
        task[field]=parseFloat(el.val())||0;
        el.val(task[field]);

      } else {
        task[field] = el.val();
      }
      self.master.endTransaction();

    } else if (field == "name" && el.val() == "") { // remove unfilled task even if not changed
      if (task.getRow()!=0) {
        task.deleteTask();
        self.master.gantt.synchHighlight();
      }else {
        el.oneTime(1,"foc",function(){$(this).focus()}); //
        event.preventDefault();
        //return false;
      }

    }
  });

  //cursor key movement
  taskRow.find("input").keydown(function (event) {
    var theCell = $(this);
    var theTd = theCell.parent();
    var theRow = theTd.parent();
    var col = theTd.prevAll("td").length;

    var ret = true;
    if (!event.ctrlKey) {
      switch (event.keyCode) {

        case 37: //left arrow
          if (!theCell.is(":text") || (!this.selectionEnd || this.selectionEnd == 0))
            theTd.prev().find("input").focus();
          break;
        case 39: //right arrow
          if (!theCell.is(":text") || (!this.selectionEnd || this.selectionEnd == this.value.length))
            theTd.next().find("input").focus();
          break;

        case 38: //up arrow
          //var prevRow = theRow.prev();
          var prevRow = theRow.prevAll(":visible:first");
          var td = prevRow.find("td").eq(col);
          var inp = td.find("input");

          if (inp.length > 0)
            inp.focus();
          break;
        case 40: //down arrow
          //var nextRow = theRow.next();
          var nextRow = theRow.nextAll(":visible:first");
          var td = nextRow.find("td").eq(col);
          var inp = td.find("input");
          if (inp.length > 0)
            inp.focus();
          else
            nextRow.click(); //create a new row
          break;
        case 36: //home
          break;
        case 35: //end
          break;

        case 9: //tab
        case 13: //enter
          break;
      }
    }
    return ret;

  }).focus(function () {
    $(this).closest("tr").click();
  });


  //change status
  taskRow.find(".taskStatus").click(function () {
    var el = $(this);
    var tr = el.closest("[taskid]");
    var taskId = tr.attr("taskid");
    var task = self.master.getTask(taskId);

    var changer = $.JST.createFromTemplate({}, "CHANGE_STATUS");
    changer.find("[status=" + task.status + "]").addClass("selected");
    changer.find(".taskStatus").click(function (e) {
      e.stopPropagation();
      var newStatus = $(this).attr("status");
      changer.remove();
      self.master.beginTransaction();
      task.changeStatus(newStatus);
      self.master.endTransaction();
      el.attr("status", task.status);
    });
    el.oneTime(3000, "hideChanger", function () {
      changer.remove();
    });
    el.after(changer);
  });


  //bind row selection
  taskRow.click(function (event) {
    var row = $(this);
    //console.debug("taskRow.click",row.attr("taskid"),event.target)
    //var isSel = row.hasClass("rowSelected");
    row.closest("table").find(".rowSelected").removeClass("rowSelected");
    row.addClass("rowSelected");

    //set current task
    self.master.currentTask = self.master.getTask(row.attr("taskId"));

    //move highlighter
    self.master.gantt.synchHighlight();

    //if offscreen scroll to element
    var top = row.position().top;
    if (top > self.element.parent().height()) {
      row.offsetParent().scrollTop(top - self.element.parent().height() + 100);
    } else if (top <= 40) {
      row.offsetParent().scrollTop(row.offsetParent().scrollTop() - 40 + top);
    }
  });

};


GridEditor.prototype.openFullEditor = function (task, taskRow, editOnlyAssig) {
	console.log('openFullEditor data------------------',task, taskRow, editOnlyAssig);
  var self = this;

  if (!self.master.permissions.canSeePopEdit)
    return;

  //task editor in popup
  var taskId =task.id// taskRow.attr("taskId");
  //console.debug(task);
  console.log('openFullEditor taskId------------------',taskId);
  //make task editor
  var taskEditor = $.JST.createFromTemplate(task, "TASK_EDITOR");

  //hide task data if editing assig only
  if (editOnlyAssig) {
    taskEditor.find(".taskData").hide();
    taskEditor.find(".assigsTableWrapper").height(455);
    taskEditor.prepend("<h1>\""+task.name+"\"</h1>");
  }

  //got to extended editor
  if (task.isNew()|| !self.master.permissions.canSeeFullEdit){
    taskEditor.find("#taskFullEditor").remove();
  } else {
    taskEditor.bind("openFullEditor.gantt",function () {
      window.location.href=contextPath+"/applications/teamwork/task/taskEditor.jsp?CM=ED&OBJID="+task.id;
    });
  }


  taskEditor.find("#name").val(task.name);
  taskEditor.find("#description").val(task.description);
  taskEditor.find("#code").val(task.code);
  taskEditor.find("#progress").val(task.progress ? parseFloat(task.progress) : 0).prop("readonly",task.progressByWorklog==true);
  taskEditor.find("#progressByWorklog").prop("checked",task.progressByWorklog);
  taskEditor.find("#status").val(task.status);
  taskEditor.find("#type").val(task.typeId);
  taskEditor.find("#type_txt").val(task.type);
  taskEditor.find("#relevance").val(task.relevance);
  //cvc_redraw(taskEditor.find(".cvcComponent"));


  if (task.startIsMilestone)
    taskEditor.find("#startIsMilestone").prop("checked", true);
  if (task.endIsMilestone)
    taskEditor.find("#endIsMilestone").prop("checked", true);

  taskEditor.find("#duration").val(task.duration);
  var startDate = taskEditor.find("#start");
  startDate.val(new Date(task.start).format());
  //start is readonly in case of deps
  if (task.depends || !this.master.permissions.canWrite && !task.canWrite) {
    startDate.attr("readonly", "true");
  } else {
    startDate.removeAttr("readonly");
  }

  taskEditor.find("#end").val(new Date(task.end).format());

  //make assignments table
  var assigsTable = taskEditor.find("#assigsTable");
  assigsTable.find("[assId]").remove();
  // loop on assignments
  for (var i = 0; i < task.assigs.length; i++) {
    var assig = task.assigs[i];
    var assigRow = $.JST.createFromTemplate({task: task, assig: assig}, "ASSIGNMENT_ROW");
    assigsTable.append(assigRow);
  }

  if (!self.master.permissions.canWrite || !task.canWrite) {
    taskEditor.find("input,textarea").prop("readOnly", true);
    taskEditor.find("input:checkbox,select").prop("disabled", true);
    taskEditor.find("#saveButton").remove();
    taskEditor.find(".button").addClass("disabled");

  } else {

    //bind dateField on dates, duration
    taskEditor.find("#start,#end,#duration").click(function () {
      var input = $(this);
      if (input.is("[entrytype=DATE]")) {
        input.dateField({
          inputField: input,
          callback:   function (d) {$(this).blur();}
        });
      }
    }).blur(function () {
      var inp = $(this);
      if (inp.validateField()) {
        resynchDates(inp, taskEditor.find("[name=start]"), taskEditor.find("[name=startIsMilestone]"), taskEditor.find("[name=duration]"), taskEditor.find("[name=end]"), taskEditor.find("[name=endIsMilestone]"));
        //workload computation
        if (typeof(workloadDatesChanged)=="function")
          workloadDatesChanged();
      }
    });

    taskEditor.find("#startIsMilestone,#endIsMilestone").click(function () {
      var inp = $(this);
      resynchDates(inp, taskEditor.find("[name=start]"), taskEditor.find("[name=startIsMilestone]"), taskEditor.find("[name=duration]"), taskEditor.find("[name=end]"), taskEditor.find("[name=endIsMilestone]"));
    });

    //bind add assignment
    var cnt=0;
    taskEditor.find("#addAssig").click(function () {
      cnt++;
      var assigsTable = taskEditor.find("#assigsTable");
      var assigRow = $.JST.createFromTemplate({task: task, assig: {id: "tmp_" + new Date().getTime()+"_"+cnt}}, "ASSIGNMENT_ROW");
      assigsTable.append(assigRow);
      $("#bwinPopupd").scrollTop(10000);
    }).click();

    //save task
    taskEditor.bind("saveFullEditor.gantt",function () {
      //console.debug("saveFullEditor");
      var task = self.master.getTask(taskId); // get task again because in case of rollback old task is lost
      console.log('self.master-------------',self.master)
      console.log(' taskId------------',taskId)
      self.master.beginTransaction();
      console.log('taskEditor==============',taskEditor)
      task.name = taskEditor.find("#name").val();
      console.log('taskEditor.find("#name")----------------------',taskEditor.find("#name"))
      console.log('val----------------------',task.name)
      task.description = taskEditor.find("#description").val();
      task.code = taskEditor.find("#code").val();
      task.progress = parseFloat(taskEditor.find("#progress").val());
      task.duration = parseInt(taskEditor.find("#duration").val()); //bicch rimosso perchè devono essere ricalcolata dalla start end, altrimenti sbaglia
      task.startIsMilestone = taskEditor.find("#startIsMilestone").is(":checked");
      task.endIsMilestone = taskEditor.find("#endIsMilestone").is(":checked");

      task.type = taskEditor.find("#type_txt").val();
      task.typeId = taskEditor.find("#type").val();
      task.relevance = taskEditor.find("#relevance").val();
      task.progressByWorklog= taskEditor.find("#progressByWorklog").is(":checked");

      //set assignments
      var cnt=0;
      taskEditor.find("tr[assId]").each(function () {
        var trAss = $(this);
        var assId = trAss.attr("assId");
        var resId = trAss.find("[name=resourceId]").val();
        var resName = trAss.find("[name=resourceId_txt]").val(); // from smartcombo text input part
        var roleId = trAss.find("[name=roleId]").val();
        var effort = millisFromString(trAss.find("[name=effort]").val(),true);

        //check if the selected resource exists in ganttMaster.resources
        var res= self.master.getOrCreateResource(resId,resName);

        //if resource is not found nor created
        if (!res)
          return;

        //check if an existing assig has been deleted and re-created with the same values
        var found = false;
        for (var i = 0; i < task.assigs.length; i++) {
          var ass = task.assigs[i];

          if (assId == ass.id) {
            ass.effort = effort;
            ass.roleId = roleId;
            ass.resourceId = res.id;
            ass.touched = true;
            found = true;
            break;

          } else if (roleId == ass.roleId && res.id == ass.resourceId) {
            ass.effort = effort;
            ass.touched = true;
            found = true;
            break;

          }
        }

        if (!found && resId && roleId) { //insert
          cnt++;
          //console.debug("adding assig row:", assId,resId,resName,roleId,effort)
          var ass = task.createAssignment("tmp_" + new Date().getTime()+"_"+cnt, resId, roleId, effort);
          ass.touched = true;
        }

      });

      //console.debug("task.assigs",task.assigs,task.assigs.length)
      //remove untouched assigs
      task.assigs = task.assigs.filter(function (ass) {
        var ret = ass.touched;
        delete ass.touched;
        return ret;
      });
      //console.debug("task.assigs",task.assigs,task.assigs.length)

      //change dates
      task.setPeriod(Date.parseString(taskEditor.find("#start").val()).getTime(), Date.parseString(taskEditor.find("#end").val()).getTime() + (3600000 * 22));

      //change status
      task.changeStatus(taskEditor.find("#status").val());

      if (self.master.endTransaction()) {
        taskEditor.find(":input").updateOldValue();
        closeBlackPopup();
      }

    });
  }

  taskEditor.attr("alertonchange","true");
  var ndo = createModalPopup(800, 450).append(taskEditor);//.append("<div style='height:800px; background-color:red;'></div>")
  //var ndo = createModalPopup(800, 650).append("<div style='height:300px; background-color:red;'></div>")

  //workload computation
  if (typeof(workloadDatesChanged)=="function")
    workloadDatesChanged();



};
