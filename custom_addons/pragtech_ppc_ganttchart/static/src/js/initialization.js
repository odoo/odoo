var context_dict;
var project_id;
var data_dict = {};

if (window.location.href.includes("#id="))
	{
		var str = window.location.href.split("#id=")
		project_id = parseInt(str[1][0])
	}
else
	{
		var str = window.location.href.split("project_id=")
		if (str[1]){
		project_id = parseInt(str[1][0])
		}
//		else
//		{
//		alert('something went wrong')
//		}
	}
if (!project_id)
	{
		alert('Please select valid project.')
	} 

var data_dict = {};
$.ajax({
			type : "POST",
			async : false,
			dataType : 'json',
			url : '/get_project_tasks',
			contentType : "application/json; charset=utf-8",
			data : JSON
					.stringify({
						'jsonrpc' : "2.0",
						'method' : "call",
						"params" : {
							'project_id' : project_id
						}
					}),
			success : function(task_data) {
				console.log('result----------------------',task_data)
				data_dict = JSON.parse(task_data.result);
			},
			error : function(
					data) {alert('Please select valid project')}
		});


$(function() {
	var canWrite = true; // this is the default for test purposes

	// here starts gantt initialization
	ge = new GanttMaster();
	var workSpace = $("#workSpace");

	workSpace
			.css({
				width : $(
						window)
						.width(),
				height : $(
						window)
						.height()
			});

	ge
			.init(workSpace);
	loadI18n(); // overwrite with localized ones

	// in order to force compute the best-fitting zoom level
	delete ge.gantt.zoom;

	var project = loadFromLocalStorage();

	 console.log('project-----------',project)
	if (!project.canWrite)

		$(
				".ganttButtonBar button.requireWrite")
				.attr(
						"disabled",
						"true");

	ge
			.loadProject(project);
	ge
			.checkpoint(); // empty the undo stack

	ge.editor.element
			.oneTime(
					100,
					"cl",
					function() {
						$(
								this)
								.find(
										"tr.emptyRow:first")
								.click()
					});

	$(
			window)
			.resize(
					function() {
						console
								.log('2222222222222222222')
						workSpace
								.css({
									width : $(
											window)
											.width() - 1,
									height : $(
											window)
											.height()
											- workSpace
													.position().top
								});
						workSpace
								.trigger("resize.gantt");
					})
			.oneTime(
					150,
					"resize",
					function() {
						$(
								this)
								.trigger(
										"resize")
					});

});

function loadGanttFromServer(
		taskId,
		callback) {
	console
			.log('33333333333333333333')

	// this is a simulation: load data from the local storage if you have
	// already played with the demo or a textarea with starting demo data
	loadFromLocalStorage();

	// this is the real implementation
	/*
	 * //var taskId = $("#taskSelector").val(); var prof = new
	 * Profiler("loadServerSide"); prof.reset();
	 *
	 * $.getJSON("ganttAjaxController.jsp", {CM:"LOADPROJECT",taskId:taskId},
	 * function(response) { //console.debug(response); if (response.ok) {
	 * prof.stop();
	 *
	 * ge.loadProject(response.project); ge.checkpoint(); //empty the undo stack
	 *
	 * if (typeof(callback)=="function") { callback(response); } } else {
	 * jsonErrorHandling(response); } });
	 */
}

self
		.$(
				"#close_button")
		.on(
				"click",
				function(
						e) {
					history
							.back();
				});

function saveGanttOnServer() {
	// this is a simulation: save data to the local storage or to the textarea
	saveInLocalStorage();
	var prj = ge.saveProject();
	delete prj.resources;
	delete prj.roles;
		console.log('yggfgfgfgfggf',JSON
					.stringify({
							'CM' : "SVPROJECT",
							'prj' : prj
						}),)

	// var prof = new Profiler("saveServerSide");
	// prof.reset();
	if (ge.deletedTaskIds.length > 0) {
		if (!confirm("TASK_THAT_WILL_BE_REMOVED\n"
				+ ge.deletedTaskIds.length)) {
			return;
		}
	}
	$.ajax({
					type : "POST",
                    async : false,
                    dataType : 'json',
                    url : '/save_project_tasks',
			contentType : "application/json; charset=utf-8",

						data :JSON
					.stringify({
					'jsonrpc' : "2.0",
						'method' : "call",
						"params" : {
							'CM' : "SVPROJECT",
							'project' : prj
							}
						}),

						success : function(response) {
//							if (response.ok) {
//								prof.stop();
								console.log("\n\nreaponse",response)

								if (response.result) {
								console.log("\n\nreaponse",response.result)
									ge.loadProject(response.result); // must
									// reload
									// as
									// "tmp_"
									// ids
									// are
									// now
									// the
									// good
									// ones
								} else {
									ge.reset();
								}
//								}
//							} else {
//								var errMsg = "Errors saving project\n";
//								if (response.message) {
//									errMsg = errMsg
//											+ response.message
//											+ "\n";
//								}
//
//								if (response.errorMessages.length) {
//									errMsg += response.errorMessages
//											.join("\n");
//								}
//
//								alert(errMsg);
//							}
						}

					});

}

function newProject() {
	console
			.log('5555555555555555555')
	clearGantt();
}

// ------------------------------------------- Create some demo data
// ------------------------------------------------------
function setRoles() {
	console
			.log('6666666666666666666')
	ge.roles = [
			{
				id : "tmp_1",
				name : "Project Manager"
			},
			{
				id : "tmp_2",
				name : "Worker"
			},
			{
				id : "tmp_3",
				name : "Stakeholder"
			},
			{
				id : "tmp_4",
				name : "Customer"
			} ];
}

function setResource() {
	console
			.log('7777777777777777777')
	var res = [];
	for (var i = 1; i <= 10; i++) {
		res
				.push({
					id : "tmp_"
							+ i,
					name : "Resource "
							+ i
				});
	}
	ge.resources = res;
}

function editResources() {
	console
			.log('888888888888888888')
}

function clearGantt() {
	ge
			.reset();
}

function loadI18n() {
	console
			.log('999999999999999999')
	GanttMaster.messages = {
		"CANNOT_WRITE" : "CANNOT_WRITE",
		"CHANGE_OUT_OF_SCOPE" : "NO_RIGHTS_FOR_UPDATE_PARENTS_OUT_OF_EDITOR_SCOPE",
		"START_IS_MILESTONE" : "START_IS_MILESTONE",
		"END_IS_MILESTONE" : "END_IS_MILESTONE",
		"TASK_HAS_CONSTRAINTS" : "TASK_HAS_CONSTRAINTS",
		"GANTT_ERROR_DEPENDS_ON_OPEN_TASK" : "GANTT_ERROR_DEPENDS_ON_OPEN_TASK",
		"GANTT_ERROR_DESCENDANT_OF_CLOSED_TASK" : "GANTT_ERROR_DESCENDANT_OF_CLOSED_TASK",
		"TASK_HAS_EXTERNAL_DEPS" : "TASK_HAS_EXTERNAL_DEPS",
		"GANTT_ERROR_LOADING_DATA_TASK_REMOVED" : "GANTT_ERROR_LOADING_DATA_TASK_REMOVED",
		"ERROR_SETTING_DATES" : "ERROR_SETTING_DATES",
		"CIRCULAR_REFERENCE" : "CIRCULAR_REFERENCE",
		"CANNOT_DEPENDS_ON_ANCESTORS" : "CANNOT_DEPENDS_ON_ANCESTORS",
		"CANNOT_DEPENDS_ON_DESCENDANTS" : "CANNOT_DEPENDS_ON_DESCENDANTS",
		"INVALID_DATE_FORMAT" : "INVALID_DATE_FORMAT",
		"TASK_MOVE_INCONSISTENT_LEVEL" : "TASK_MOVE_INCONSISTENT_LEVEL",

		"GANTT_QUARTER_SHORT" : "trim.",
		"GANTT_SEMESTER_SHORT" : "sem."
	};
}

// ------------------------------------------- Get project file as JSON (used
// for migrate project from gantt to Teamwork)
// ------------------------------------------------------
function getFile() {
	$(
			"#gimBaPrj")
			.val(
					JSON
							.stringify(ge
									.saveProject()));
	$(
			"#gimmeBack")
			.submit();
	$(
			"#gimBaPrj")
			.val(
					"");

	/*
	 * var uriContent = "data:text/html;charset=utf-8," +
	 * encodeURIComponent(JSON.stringify(prj));
	 * neww=window.open(uriContent,"dl");
	 */
}

function loadFromLocalStorage() {
	var ret = null;
	if (localStorage) {
		console
				.log('localStorage--------')
		if (localStorage
				.getObject("teamworkGantDemo")) {
			ret = localStorage
					.getObject("teamworkGantDemo");
		}
	}
	var ret = null;
	// if not found create a new example task
	// console
	// 		.log(
	// 				'ret.tasks.length-----------',
	// 				data_dict)
	
					if (!ret
			|| !ret.tasks
			|| ret.tasks.length == 0) {
		// console
		// 		.log('if---------------------------------')
		// var data_dict;
		// $.ajax({
		// type: "POST",
		// async:false,
		// dataType: 'json',
		// url: '/get_project_tasks',
		// contentType: "application/json; charset=utf-8",
		// data: JSON.stringify({'jsonrpc': "2.0", 'method': "call", "params":
		// {}}),
		// success: function (task_data) {
		// console.log('result----------------------',task_data)
		// data_dict= JSON.parse(task_data.result);
		// console.log('11data_dict-----------',data_dict)
		// },
		// error: function(data){
		// console.log('Json failed-----------',data)
		// console.log("ERROR ", data);
		// }});

		// console
		// 		.log(
		// 				'final data_dict-----------',
		// 				data_dict)
		data_dict = JSON
				.parse(data_dict);
		ret = {
			"tasks" : data_dict,
			"selectedRow" : 2,
			"deletedTaskIds" : [],
			"resources" : [
					{
						"id" : "tmp_1",
						"name" : "Resource 1"
					},
					{
						"id" : "tmp_2",
						"name" : "Resource 2"
					},
					{
						"id" : "tmp_3",
						"name" : "Resource 3"
					},
					{
						"id" : "tmp_4",
						"name" : "Resource 4"
					} ],
			"roles" : [
					{
						"id" : "tmp_1",
						"name" : "Project Manager"
					},
					{
						"id" : "tmp_2",
						"name" : "Worker"
					},
					{
						"id" : "tmp_3",
						"name" : "Stakeholder"
					},
					{
						"id" : "tmp_4",
						"name" : "Customer"
					} ],
			"canWrite" : true,
			"canWriteOnParent" : true,
			"zoom" : "w3"
		}
		
		
//		console.debug("collapseAll");
//		var arr=[]
//		  console.log('in init this---------------',ret.tasks)
//		  arr=ret.tasks
//		  console.log('arr-----------',arr,typeof(arr),arr[0])
////		  console.log('arr collapsed-----------',arr[0].collapsed)
////		  arr[0].collapsed = true;
////			  console.log('ctask---------------',this.currentTask)
////		    var desc = ret.tasks[0].getDescendant();
////		    for (var i=0; i<desc.length; i++) {
////		      if (desc[i].isParent()) // set collapsed only if is a parent
////		    	  console.log("desc[i]--------------",desc[i])
////		        desc[i].collapsed = true;
////		      desc[i].rowElement.hide();
////		    }
////		  this.redraw();
////		    this.storeCollapsedTasks();
		
		
		
//		if (ret.tasks[0]) {
//			var offset = new Date()
//					.getTime()
//					- ret.tasks[0].start;
//			console.log('collapsing-----',ret.tasks[0].collapsed)
//			for (var i = 0; i < ret.tasks.length; i++) {
//				ret.tasks[i].start = ret.tasks[i].start
//
////				console.log('iswbs------',ret.tasks[3].id,ret.tasks[3].name,this)
////				ret.tasks[3].collapsed=true
////				ge = new GanttMaster(this);
////				console.log('ge------',ge)
////				ge.Ganttmaster.redraw(this);
//			} // loop end
//		}
	} // if end

	// else{
	// console.log('else---------------------------------')
	// ret=undefined;
	// data_dict=fetch_data();
	// console.log('else final data_dict-----------',data_dict)
	// data_dict= JSON.parse(data_dict);
	// ret= {
	// "tasks": data_dict,
	// "selectedRow": 2, "deletedTaskIds": [],
	// "resources": [
	// {"id": "tmp_1", "name": "Resource 1"},
	// {"id": "tmp_2", "name": "Resource 2"},
	// {"id": "tmp_3", "name": "Resource 3"},
	// {"id": "tmp_4", "name": "Resource 4"}
	// ],
	// "roles": [
	// {"id": "tmp_1", "name": "Project Manager"},
	// {"id": "tmp_2", "name": "Worker"},
	// {"id": "tmp_3", "name": "Stakeholder"},
	// {"id": "tmp_4", "name": "Customer"}
	// ], "canWrite": true, "canWriteOnParent": true, "zoom": "w3"}
	//  
	// 
	// console.log('else returning ret---------------',ret)
	// }
	console.log('else returning ret---------------',ret)
	return ret;
}

function saveInLocalStorage() {
	var prj = ge
			.saveProject();
			console.log("\n\n-----prj-------",prj)
	if (localStorage) {
		localStorage
				.setObject(
						"teamworkGantDemo",
						prj);
	}
}

// ------------------------------------------- Open a black popup for managing
// resources. This is only an axample of implementation (usually resources come
// from server) ------------------------------------------------------
function editResources() {

	// make resource editor
	var resourceEditor = $.JST
			.createFromTemplate(
					{},
					"RESOURCE_EDITOR");
	var resTbl = resourceEditor
			.find("#resourcesTable");

	for (var i = 0; i < ge.resources.length; i++) {
		console
				.log(
						'i2-------------',
						i)
		var res = ge.resources[i];
		resTbl
				.append($.JST
						.createFromTemplate(
								res,
								"RESOURCE_ROW"))
	}

	// bind add resource
	resourceEditor
			.find(
					"#addResource")
			.click(
					function() {
						resTbl
								.append($.JST
										.createFromTemplate(
												{
													id : "new",
													name : "resource"
												},
												"RESOURCE_ROW"))
					});

	// bind save event
	resourceEditor
			.find(
					"#resSaveButton")
			.click(
					function() {
						var newRes = [];
						// find for deleted res
						for (var i = 0; i < ge.resources.length; i++) {
							var res = ge.resources[i];
							var row = resourceEditor
									.find("[resId="
											+ res.id
											+ "]");
							if (row.length > 0) {
								// if still there save it
								var name = row
										.find(
												"input[name]")
										.val();
								if (name
										&& name != "")
									res.name = name;
								newRes
										.push(res);
							} else {
								// remove assignments
								for (var j = 0; j < ge.tasks.length; j++) {
									var task = ge.tasks[j];
									var newAss = [];
									for (var k = 0; k < task.assigs.length; k++) {
										var ass = task.assigs[k];
										if (ass.resourceId != res.id)
											newAss
													.push(ass);
									}
									task.assigs = newAss;
								}
							}
						}

						// loop on new rows
						var cnt = 0
						resourceEditor
								.find(
										"[resId=new]")
								.each(
										function() {
											cnt++;
											var row = $(this);
											var name = row
													.find(
															"input[name]")
													.val();
											if (name
													&& name != "")
												newRes
														.push(new Resource(
																"tmp_"
																		+ new Date()
																				.getTime()
																		+ "_"
																		+ cnt,
																name));
										});

						ge.resources = newRes;

						closeBlackPopup();
						ge
								.redraw();
					});

	var ndo = createModalPopup(
			400,
			500)
			.append(
					resourceEditor);
}
//}//If ends