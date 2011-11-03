//v.1.3 build 100805

/*
Copyright DHTMLX LTD. http://www.dhtmlx.com
To use this component please contact sales@dhtmlx.com to obtain license
*/

/*_TOPICS_
 * @0:Initialization
 * @1:Add/delete
 * @2:Lookup
 * @3:Appearance
 * @4:Private
 * @5:Handlers
 * @6:Load/Save data
 * @7:Printing
 */

/**
 *  @desc: GanttProjectInfo constructor
 *  @param: id - id of the project
 *  @param: name - name of the project
 *  @param: startDate - start date of the project (JavaScript Date object)
 *  @type:  public
 *  @topic: 0
 */
function GanttProjectInfo(id, name, startDate)
{
    this.Id = id;
    this.Name = name;
    this.StartDate = startDate;
    this.ParentTasks = [];
}
/**
 * @desc:  Delete specified task
 * @param: id - id of the task to be deleted
 * @type:  public
 * @topic: 1
 * @edition: Professional
 */
GanttProjectInfo.prototype.deleteTask = function(id)
{
    var task = this.getTaskById(id);
    if (task) {
        if (!task.ParentTask) {

            for (var i = 0; i < this.ParentTasks.length; i++) {

                if (this.ParentTasks[i].Id == id) {

                    if (this.ParentTasks[i].nextParentTask) {

                        if (this.ParentTasks[i].previousParentTask) {
                            this.ParentTasks[i].previousParentTask.nextParentTask = this.ParentTasks[i].nextParentTask;
                            this.ParentTasks[i].nextParentTask.previousParentTask = this.ParentTasks[i].previousParentTask;
                        } else {
                            this.ParentTasks[i].nextParentTask.previousParentTask = null;
                        }

                    } else {
                        if (this.ParentTasks[i].previousParentTask) {
                            this.ParentTasks[i].previousParentTask.nextParentTask = null;
                        }
                    }

                    this.ParentTasks[i] = null;
                    this.ParentTasks.splice(i, 1);
                    break;
                }
            }

        } else
        {
            var parentTask = task.ParentTask;
            for (var i = 0; i < parentTask.ChildTasks.length; i++) {

                if (parentTask.ChildTasks[i].Id == id) {

                    if (parentTask.ChildTasks[i].nextChildTask) {

                        if (parentTask.ChildTasks[i].previousChildTask) {

                            parentTask.ChildTasks[i].previousChildTask.nextChildTask = parentTask.ChildTasks[i].nextChildTask;
                            parentTask.ChildTasks[i].nextChildTask.previousChildTask = parentTask.ChildTasks[i].previousChildTask;

                        } else {
                            parentTask.ChildTasks[i].nextChildTask.previousChildTask = null;
                        }

                    } else {
                        if (parentTask.ChildTasks[i].previousChildTask) {
                            parentTask.ChildTasks[i].previousChildTask.nextChildTask = null;
                        }
                    }

                    parentTask.ChildTasks[i] = null;
                    parentTask.ChildTasks.splice(i, 1);
                    break;
                }

            }
        }
    }
};
/**
 * @desc:  Addition of the task in project
 * @param: task - TaskInfo object
 * @type:  public
 * @topic: 1
 */
GanttProjectInfo.prototype.addTask = function(task)
{
    this.ParentTasks.push(task);
    task.setProject(this);
};
/**
 * @desc: get object task by id
 * @param: id - id of task
 * @type: public
 * @topic: 2
 */
GanttProjectInfo.prototype.getTaskById = function(id)
{
    for (var j = 0; j < this.ParentTasks.length; j++)
    {
        var task = this.getTaskByIdInTree(this.ParentTasks[j], id);
        if (task) return task;
    }
    return null;
};
/**
 * @desc: get object task by id
 * @param: parentTask -(object) parent task
 * @param: id - id of current task
 * @type: private
 * @topic: 2
 */
GanttProjectInfo.prototype.getTaskByIdInTree = function(parentTask, id)
{
    if (parentTask.Id == id)
    {
        return parentTask;

    } else
    {
        for (var i = 0; i < parentTask.ChildTasks.length; i++) {

            if (parentTask.ChildTasks[i].Id == id)
            {
                return parentTask.ChildTasks[i];
            }
            if (parentTask.ChildTasks[i].ChildTasks.length > 0)
            {
                if (parentTask.ChildTasks[i].ChildTasks.length > 0)
                {
                    var cTask = this.getTaskByIdInTree(parentTask.ChildTasks[i], id);
                    if (cTask) return cTask;
                }
            }
        }

    }
    return null;
};
/**
 * @desc: GanttTaskInfo constructor
 * @param: id - specifies id of task
 * @param: name  - specifies name of task
 * @param: est  - specifies Estimated Start Date of task
 * @param: duration - specifies duration of task in hours
 * @param: percentCompleted - specifies percentCompleted of task
 * @param: predecessorTaskId - specifies predecessorTask Id of task
 * @type:  public
 * @topic: 0
 */
function GanttTaskInfo(id, name, est, duration, percentCompleted, predecessorTaskId)
{
    this.Id = id;
    this.Name = name;
    this.EST = est;
    this.Duration = duration;
    this.PercentCompleted = percentCompleted;
    this.PredecessorTaskId = predecessorTaskId;
    this.ChildTasks = [];
    this.ChildPredTasks = [];
    this.ParentTask = null;
    this.PredecessorTask = null;
    this.Project = null;
    this.nextChildTask = null;
    this.previousChildTask = null;
    this.nextParentTask = null;
    this.previousParentTask = null;
}
/**
 * @desc: Addition of child task to the parent task
 * @param: task - (object) task
 * @type: public
 * @topic: 1
 */
GanttTaskInfo.prototype.addChildTask = function(task)
{
    this.ChildTasks.push(task);
    task.ParentTask = this;
};
/**
 * @desc: set project to this task and its children
 * @param: project - (object) project
 * @type: private
 * @topic: 0
 */
GanttTaskInfo.prototype.setProject = function(project)
{
    this.Project = project;
    for (var j = 0; j < this.ChildTasks.length; j++)
    {
        this.ChildTasks[j].setProject(project);
    }
};
/**
 * @desc: private GanttTask constructor
 * @param: taskInfo - (object)GanttTaskInfo
 * @param: project - (object) GanttProject
 * @param: chart - (object)GanttChart
 * @type:  public
 * @topic: 0
 */
function GanttTask(taskInfo, project, chart)
{
    this.isTask = true;

    this.Chart = chart;
    this.Project = project;
    this.TaskInfo = taskInfo;

    //control variables
    this.checkMove = false;
    this.checkResize = false;
    this.moveChild = false;

    this.maxPosXMove = -1;
    this.minPosXMove = -1;
    this.maxWidthResize = -1;
    this.minWidthResize = -1;
    this.posX = 0;
    this.posY = 0;
    this.MouseX = 0;
    this.taskItemWidth = 0;
    this.isHide = false;
    this._heightHideTasks = 0;
    this._isOpen = true;

    this.descrTask = null;
    this.cTaskItem = null;
    this.cTaskNameItem = null;

    this.parentTask = null;
    this.predTask = null;
    this.childTask = [];
    this.childPredTask = [];
    this.nextChildTask = null;
    this.previousChildTask = null;
    this.nextParentTask = null;
    this.previousParentTask = null;

}
/**
 * @desc:  private GanttProject constructor
 * @type:  public
 * @topic: 0
 */
function GanttProject(Chart, projectInfo)
{
    this.isProject = true;

    this.nextProject = null;
    this.previousProject = null;
    this.arrTasks = [];
    this.Project = projectInfo;
    this.Chart = Chart;
    this.percentCompleted = 0;
    this.Duration = 0;

    this.descrProject = null;
    this.projectItem = null;
    this.projectNameItem = null;

    this.posY = 0;
    this.posX = 0;
}
/**
 *  @desc: check width of projectNameItem
 *  @type: private
 *  @topic: 4
 */
GanttProject.prototype.checkWidthProjectNameItem = function()
{
    if (this.projectNameItem.offsetWidth + this.projectNameItem.offsetLeft > this.Chart.maxWidthPanelNames)
    {
        var width = this.projectNameItem.offsetWidth + this.projectNameItem.offsetLeft - this.Chart.maxWidthPanelNames;
        var countChar = Math.round(width / (this.projectNameItem.offsetWidth / this.projectNameItem.firstChild.length));
        var pName = this.Project.Name.substring(0, this.projectNameItem.firstChild.length - countChar - 3);
        pName += "...";
        this.projectNameItem.innerHTML = pName;
    }
};
/**
 *  @desc: create GanttProject.
 *  @type: private
 *  @topic: 0
 */
GanttProject.prototype.create = function()
{
    var containerTasks = this.Chart.oData.firstChild;

    this.posX = (this.Project.StartDate - this.Chart.startDate) / (60 * 60 * 1000) * this.Chart.hourInPixels;

    if (this.previousProject)
    {
        if (this.previousProject.arrTasks.length > 0) {
            var lastChildTask = this.Chart.getLastChildTask(this.previousProject.arrTasks[this.previousProject.arrTasks.length - 1]);
            this.posY = parseInt(lastChildTask.cTaskItem[0].style.top) + this.Chart.heightTaskItem + 11;
        } else {
            this.posY = parseInt(this.previousProject.projectItem[0].style.top) + this.Chart.heightTaskItem + 11;
        }
    } else {
        this.posY = 6;
    }

    if (this.Chart._showTreePanel) {

        var containerNames = this.Chart.panelNames.firstChild;
        this.projectNameItem = this.createProjectNameItem();
        containerNames.appendChild(this.projectNameItem);
        this.checkWidthProjectNameItem();

    }
    this.projectItem = [this.createProjectItem(),[]];
    containerTasks.appendChild(this.projectItem[0]);

    if (this.Chart.isShowDescProject) {
        containerTasks.appendChild(this.createDescrProject());
    }

    this.addDayInPanelTime();
};
/**
 *  @desc: GanttChart constructor
 *  @type: public
 *  @topic: 0
 */
function GanttChart()
{
    this.Error = new GanttError();
    this.dhtmlXMLSenderObject = new dhtmlXMLSenderObject(this);

    //settings
    this.heightTaskItem = 12;
    this.dayInPixels = 24;
    this.hoursInDay = 8;
    this._showTreePanel = true;
    this._showTooltip = true;
    this.isShowDescTask = false;
    this.isShowDescProject = false;
    this.isShowNewProject = true;
    this.isEditable = false;
    this.isShowConMenu = false;
    this.correctError = false;
    this.maxWidthPanelNames = 150;
    this.minWorkLength = 8;
    this.paramShowTask = [];
    this.paramShowProject = [];

    this.savePath = null;
    this.loadPath = null;

    //control variables
    this.divTimeInfo = null;
    this.divInfo = null;

    this.panelNames = null;
    this.panelTime = null;
    this.oData = null;
    this.content = null;
    this.panelErrors = null;
    this.contextMenu = null;

    this.hourInPixelsWork = this.dayInPixels / this.hoursInDay;
    this.hourInPixels = this.dayInPixels / 24;
    this.countDays = 0;
    this.startDate = null;
    this.initialPos = 0;

    this.contentHeight = 0;
    this.contentWidth = 0;
    this._oDataHeight = 0;

    this.Project = [];

    this.arrProjects = [];

    this.xmlLoader = null;


    this._isIE = false;
    this._isFF = false;
    this._isOpera = false;

    this._isMove = false;
    this._isResize = false;
    this._isError = false;

    this.imgs = "codebase/imgs/";
    this.stylePath = "codebase/dhtmlxgantt.css"; // used in simple printing method getPrintableHTML()

    this.shortMonthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    this.monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    this._useShortMonthNames = true;

    dhtmlxEventable(this);
}
/**
 * @desc: set path to image directory
 * @param: newPath - path to image directory, end with slash /
 * @type: public
 * @topic: 0
 * @before_init: 1
 */
GanttChart.prototype.setImagePath = function(newPath)
{
    this.imgs = newPath;
};
/**
 * @desc: set path to styles file, default is "codebase/dhtmlxgantt.css"; used in simple printing method printToWindow()
 * @param: newPath - path to styles file
 * @type: public
 * @topic: 0
 * @before_init: 1
 */
GanttChart.prototype.setStylePath = function(newPath)
{
    this.stylePath = newPath;
};
/**
 * @desc: set url which is used to save chart data with saveData() method
 * @param: newPath - url to server script.
 * @type: public
 * @topic: 6
 * @before_init: 1
 */
GanttChart.prototype.setSavePath = function(newPath)
{
    this.savePath = newPath;
};
/**
 * @desc: set url which is used to load chart data with loadData() method
 * @param: newPath - url to server script.
 * @type: public
 * @topic: 6
 * @before_init: 1
 */
GanttChart.prototype.setLoadPath = function(newPath)
{
    this.loadPath = newPath;
};
GanttChart.prototype.setCorrectError = function(isCorrectError)
{
    this.correctError = isCorrectError;
};

/**
 * @desc: enable or disable inline task description (displayed right after the task bar), and configure the shown values
 * @param: isShowDescTask - true/false show or hide
 * @param: param - comma separated list of letters: n - Name, d - Duration, e - EST, p -Percent complete. For example value "n,e" will show task name and EST date.
 * @type: public
 * @topic: 3
 * @before_init: 1
 */
GanttChart.prototype.showDescTask = function(isShowDescTask, param)
{
    this.isShowDescTask = isShowDescTask;
    var arrValues = new Array(5);

    if (this.isShowDescTask)
    {
        if (param) {
            var arrParam = param.split(",");
            for (var i = 0; i < arrParam.length; i++) {
                var k = this.getParamShowTask(arrParam[i]);
                arrValues[k] = 1;
            }
        } else {
            arrValues[this.getParamShowTask('')] = 1;
        }
        this.paramShowTask = this.getValueShowTask(arrValues);
    }

};

/**
 * @desc: enable or disable inline project description (displayed right after the project bar), and configure the shown values
 * @param: isShowDescProject - true/false show or hide
 * @param: param - comma separated list of letters: n - Name, d - Duration, s - Start date, p -Percent complete. For example value "n,s" will show project name and start date.
 * @type: public
 * @topic: 3
 * @before_init: 1
 */
GanttChart.prototype.showDescProject = function(isShowDescProject, param)
{
    this.isShowDescProject = isShowDescProject;
    var arrValues = new Array(4);

    if (this.isShowDescProject)
    {
        if (param) {
            var arrParam = param.split(",");
            for (var i = 0; i < arrParam.length; i++) {
                var k = this.getParamShowProject(arrParam[i]);
                arrValues[k] = 1;
            }
        } else {
            arrValues[this.getParamShowProject('')] = 1;
        }
        this.paramShowProject = this.getValueShowProject(arrValues);
    }

};

/**
 * @desc: enable or disable context menu in tree. it can be used for a simple task manipulations.
 * @param: show - true/false show or hide
 * @type: public
 * @topic: 3
 * @before_init: 1
 */
GanttChart.prototype.showContextMenu = function(show)
{
    this.isShowConMenu = show;
};

/**
 * @desc: set custom context menu for the tree.
 * @param: menu - an instance of dhtmlxMenu.
 * @type: public
 * @topic: 3
 * @before_init: 1
 */
GanttChart.prototype.setContextMenu = function(menu)
{
    this.showContextMenu(true);
    this.contextMenu = menu;
};

/**
 * @desc: show new project at startup. it is usefull if you have no project at all, and you need some start point. also menu is attached to this project item.
 * @param: show - true/false show or hide
 * @type: public
 * @topic: 3
 * @before_init: 1
 */
GanttChart.prototype.showNewProject = function(show)
{
    this.isShowNewProject = show;
};

GanttChart.prototype.getParamShowTask = function(param)
{
    switch (param) {
        case 'n':
            //name
            return 0;
            break;
        case 'd':
            //duration
            return 1;
            break;
        case 'e':
            //est
            return 2;
            break;
        case 'p':
            //percent complete
            return 3;
            break;
        case 's-f':
            //start-finish
            return 4;
            break;
        default:
            return 0;
            break;
    }
};

GanttChart.prototype.getParamShowProject = function(param)
{
    switch (param) {
        case 'n':
            //name
            return 0;
            break;
        case 'd':
            //duration
            return 1;
            break;
        case 's':
            //start date
            return 2;
            break;
        case 'p':
            //percent complete
            return 3;
            break;
        default:
            return 0;
            break;
    }
};

GanttChart.prototype.getValueShowTask = function(param)
{
    var arrValues = [];
    for (var i = 0; i < param.length; i++) {
        if (param[i])
        {
            switch (i) {
                case 0:
                    arrValues.push('Name');
                    break;
                case 1:
                    arrValues.push('Duration');
                    break;
                case 2:
                    arrValues.push('EST');
                    break;
                case 3:
                    arrValues.push('PercentComplete');
                    break;
                case 4:
                    arrValues.push('S-F');
                    break;
                default:
                    break;
            }
        }
    }
    return arrValues;
};

GanttChart.prototype.getValueShowProject = function(param)
{
    var arrValues = [];
    for (var i = 0; i < param.length; i++) {

        if (param[i])
        {
            switch (i) {
                case 0:
                    arrValues.push('Name');
                    break;
                case 1:
                    arrValues.push('Duration');
                    break;
                case 2:
                    arrValues.push('StartDate');
                    break;
                case 3:
                    arrValues.push('PercentComplete');
                    break;

                default:
                    break;
            }
        }
    }
    return arrValues;
};

/**
 * @desc: make Gantt Chart editable by user
 * @param: isEditable - (true/false)
 * @type: public
 * @topic: 0
 * @before_init: 1
 */
GanttChart.prototype.setEditable = function(isEditable)
{
    this.isEditable = isEditable;
};
//#__pro_feature:01102007{
/**
 * @desc: show left side tree panel
 * @param: show - (true/false)
 * @type: public
 * @topic: 0
 * @before_init: 1
 * @edition: Professional
 */
GanttChart.prototype.showTreePanel = function(show)
{
    this._showTreePanel = show;
};
/**
 * @desc: show task & project tooltip
 * @param: show - (true/false)
 * @type: public
 * @topic: 0
 * @before_init: 1
 */
GanttChart.prototype.showTooltip = function(show)
{
    this._showTooltip = show;
};
//#}
/**
 * @desc: Get current project by id
 * @param: id - id of current project
 * @type: public
 * @topic: 2
 */
GanttChart.prototype.getProjectById = function(id)
{

    for (var i = 0; i < this.arrProjects.length; i++) {

        if (this.arrProjects[i].Project.Id == id)
        {
            return this.arrProjects[i];
        }
    }
    return null;
};
/**
 * @desc: Get browser type
 * @type: private
 * @topic: 4
 */
GanttChart.prototype.getBrowserType = function()
{

    if (navigator.appName.indexOf('Explorer') != -1)
    {
        this._isIE = true;

    } else if (navigator.userAgent.indexOf('Mozilla') != -1)
    {
        this._isFF = true;

    } else if (navigator.userAgent.indexOf('Opera') != -1)
    {
        this._isOpera = true;
    }
};
/**
 * @desc: Add new project
 * @param: project - (object) GanttProjectInfo
 * @type: public
 * @topic: 0
 * @before_init: 1
 */
GanttChart.prototype.addProject = function(projectInfo)
{
    this.Project.push(projectInfo);
};
/**
 * @desc: Removal of GanttTask
 * @param: id - id of GanttTask
 * @type: public
 * @topic: 1
 */
GanttProject.prototype.deleteTask = function(id)
{
    var task = this.getTaskById(id);
    if (task) {
        this.deleteChildTask(task);
    } else {
        this.Chart.Error.throwError("DATA_INSERT_ERROR", 30, [id]);
    }
};
/**
 * @desc: Removal of GanttProject
 * @param: id - id of project
 * @type: public
 * @topic: 1
 */
GanttChart.prototype.deleteProject = function(id)
{
    var project = this.getProjectById(id);

    if (project)
    {
        if (project.arrTasks.length > 0)
        {
            while (project.arrTasks.length > 0) {
                project.deleteChildTask(project.arrTasks[0]);
            }
        }

        if (project.nextProject)project.shiftNextProject(project, -23);

        for (var i = 0; i < this.Project.length; i++) {

            if (this.Project[i].Id == project.Project.Id) {
                this.Project.splice(i, 1);
            }
        }


        if ((project.previousProject) &&
                (project.nextProject))
        {
            var previousProject = project.previousProject;
            previousProject.nextProject = project.nextProject;
        }

        if ((project.previousProject) &&
                !(project.nextProject))
        {
            var previousProject = project.previousProject;
            previousProject.nextProject = null;

        }
        if (!(project.previousProject) &&
                (project.nextProject))
        {
            var nextProject = project.nextProject;
            nextProject.previousProject = null;

        }

        for (var i = 0; i < this.arrProjects.length; i++) {

            if (this.arrProjects[i].Project.Id == id)
            {
                this.arrProjects.splice(i, 1);
            }
        }

        project.projectItem[0].parentNode.removeChild(project.projectItem[0]);

        if (this.isShowDescProject) {
            project.descrProject.parentNode.removeChild(project.descrProject);
        }

        if (this._showTreePanel) {
            project.projectNameItem.parentNode.removeChild(project.projectNameItem);
        }

        this._oDataHeight -= 11 + this.heightTaskItem;

        if (this.Project.length == 0)
        {
            if (this.isShowNewProject)
            {
                var d = new Date(this.startDate);
                var t = new Date(d.setDate(d.getDate() + 1));

                var pi = new GanttProjectInfo(1, "New project", t);
                this.Project.push(pi);
                var project = new GanttProject(this, pi);
                project.create();
                this.arrProjects.push(project);
                this._oDataHeight += 11 + this.heightTaskItem;
            }
        }


    } else {
        this.Error.throwError("DATA_INSERT_ERROR", 31, [id]);
    }
};
/**
 * @desc: Set name of project.
 * @param: name - new name of Project.
 * @type: public
 * @topic: 0
 */
GanttProject.prototype.setName = function(name)
{
    if ((name != "") && (name != null)) {
        this.Project.Name = name;
        if (this.Chart._showTreePanel)
        {
            this.projectNameItem.innerHTML = name;
            this.projectNameItem.title = name;
            this.checkWidthProjectNameItem();
        }

        if (this.Chart.isShowDescProject)this.descrProject.innerHTML = this.getDescStr();
        this.addDayInPanelTime();
    }
};
/**
 * @desc: Set Percent Completed of project
 * @param: percentCompleted - percent completed of Project
 * @type: public
 * @topic: 0
 */
GanttProject.prototype.setPercentCompleted = function(percentCompleted)
{
    percentCompleted = parseInt(percentCompleted);
    if (isNaN(percentCompleted))
    {
        this.Chart.Error.throwError("DATA_INSERT_ERROR", 6, null);
        return false;
    }

    if (percentCompleted > 100)
    {
        this.Chart.Error.throwError("DATA_INSERT_ERROR", 7, null);
        return false;

    } else if (percentCompleted < 0)
    {
        this.Chart.Error.throwError("DATA_INSERT_ERROR", 8, null);
        return false;
    }

    if ((percentCompleted > 0) && (percentCompleted < 100) && (this.percentCompleted > 0) && (this.percentCompleted < 100))
    {
        this.projectItem[0].firstChild.rows[0].cells[0].width = parseInt(percentCompleted) + "%";
        this.projectItem[0].firstChild.rows[0].cells[0].firstChild.style.width = (percentCompleted * this.Duration * this.Chart.hourInPixelsWork) / 100 + "px";
        this.projectItem[0].firstChild.rows[0].cells[1].width = (100 - parseInt(percentCompleted)) + "%";
        this.projectItem[0].firstChild.rows[0].cells[1].firstChild.style.width = ((100 - percentCompleted) * this.Duration * this.Chart.hourInPixelsWork) / 100 + "px";

    } else if (((percentCompleted == 0) || (percentCompleted == 100)) && (this.percentCompleted > 0) && (this.percentCompleted < 100))
    {
        if (percentCompleted == 0)
        {
            this.projectItem[0].firstChild.rows[0].cells[0].parentNode.removeChild(this.projectItem[0].firstChild.rows[0].cells[0]);
            this.projectItem[0].firstChild.rows[0].cells[0].width = 100 + "%";
            this.projectItem[0].firstChild.rows[0].cells[0].firstChild.style.width = this.Duration * this.Chart.hourInPixelsWork + "px";

        } else if (percentCompleted == 100)
        {
            this.projectItem[0].firstChild.rows[0].cells[1].parentNode.removeChild(this.projectItem[0].firstChild.rows[0].cells[1]);
            this.projectItem[0].firstChild.rows[0].cells[0].width = 100 + "%";
            this.projectItem[0].firstChild.rows[0].cells[0].firstChild.style.width = this.Duration * this.Chart.hourInPixelsWork + "px";
        }

    } else if (((percentCompleted == 0) || (percentCompleted == 100)) && ((this.percentCompleted == 0) || (this.percentCompleted == 100)))
    {
        if ((percentCompleted == 0) && (this.percentCompleted == 100))
        {
            this.projectItem[0].firstChild.rows[0].cells[0].firstChild.src = this.Chart.imgs + "progress_bg.png";

        } else if ((percentCompleted == 100) && (this.percentCompleted == 0))
        {
            this.projectItem[0].firstChild.rows[0].cells[0].firstChild.src = this.Chart.imgs + "parentnode_filled.png";
        }

    } else if (((percentCompleted > 0) || (percentCompleted < 100)) && ((this.percentCompleted == 0) || (this.percentCompleted == 100)))
    {
        this.projectItem[0].firstChild.rows[0].cells[0].parentNode.removeChild(this.projectItem[0].firstChild.rows[0].cells[0]);

        var cellprojectItem = document.createElement("TD");
        this.projectItem[0].firstChild.rows[0].appendChild(cellprojectItem);
        cellprojectItem.width = percentCompleted + "%";

        var imgPr = document.createElement("img");
        imgPr.style.width = (percentCompleted * this.Duration * this.Chart.hourInPixelsWork) / 100 + "px";
        imgPr.style.height = this.Chart.heightTaskItem + "px";
        cellprojectItem.appendChild(imgPr);
        imgPr.src = this.Chart.imgs + "parentnode_filled.png";


        cellprojectItem = document.createElement("TD");
        this.projectItem[0].firstChild.rows[0].appendChild(cellprojectItem);
        cellprojectItem.width = (100 - percentCompleted) + "%";
        imgPr = document.createElement("img");

        imgPr.style.width = ((100 - percentCompleted) * this.Duration * this.Chart.hourInPixelsWork) / 100 + "px";
        imgPr.style.height = this.Chart.heightTaskItem + "px";
        cellprojectItem.appendChild(imgPr);
        imgPr.src = this.Chart.imgs + "progress_bg.png";

    } else if (this.percentCompleted == -1)
    {
        if (percentCompleted == 100)
        {
            this.projectItem[0].firstChild.rows[0].cells[0].firstChild.src = this.Chart.imgs + "parentnode_filled.png";

        } else if (percentCompleted < 100 && percentCompleted > 0)
        {

            this.projectItem[0].firstChild.rows[0].cells[0].parentNode.removeChild(this.projectItem[0].firstChild.rows[0].cells[0]);

            var cellprojectItem = document.createElement("TD");
            this.projectItem[0].firstChild.rows[0].appendChild(cellprojectItem);
            cellprojectItem.width = percentCompleted + "%";

            var imgPr = document.createElement("img");
            imgPr.style.width = (percentCompleted * this.Duration * this.Chart.hourInPixelsWork) / 100 + "px";
            imgPr.style.height = this.Chart.heightTaskItem + "px";
            cellprojectItem.appendChild(imgPr);
            imgPr.src = this.Chart.imgs + "parentnode_filled.png";

            cellprojectItem = document.createElement("TD");
            this.projectItem[0].firstChild.rows[0].appendChild(cellprojectItem);
            cellprojectItem.width = (100 - percentCompleted) + "%";
            imgPr = document.createElement("img");

            imgPr.style.width = ((100 - percentCompleted) * this.Duration * this.Chart.hourInPixelsWork) / 100 + "px";
            imgPr.style.height = this.Chart.heightTaskItem + "px";
            cellprojectItem.appendChild(imgPr);
            imgPr.src = this.Chart.imgs + "progress_bg.png";
        }

    }

    this.percentCompleted = percentCompleted;
    if (this.Chart.isShowDescProject)this.descrProject.innerHTML = this.getDescStr();
    return true;
};
/**
 * @desc: Removal of child GanttTask
 * @param: task - (object)parent GanttTask
 * @type: private
 * @topic: 1
 */
GanttProject.prototype.deleteChildTask = function(task)
{
    if (task)
    {
        if (task.cTaskItem[0].style.display == "none") {
            this.Chart.openTree(task.parentTask);
        }
        //delete of connecting lines
        if (task.childPredTask.length > 0) {
            for (var i = 0; i < task.childPredTask.length; i++)
            {
                for (var t = 0; t < task.childPredTask[i].cTaskItem[1].length; t++) {
                    task.childPredTask[i].cTaskItem[1][t].parentNode.removeChild(task.childPredTask[i].cTaskItem[1][t]);
                }
                task.childPredTask[i].cTaskItem[1] = [];
                task.childPredTask[i].predTask = null;
            }
        }

        //delete child task
        if (task.childTask.length > 0) {
            while (task.childTask.length > 0) {
                this.deleteChildTask(task.childTask[0]);
            }
        }

        //shift tasks
        if (task.cTaskItem[0].style.display != "none")  task.shiftCurrentTasks(task, -23);

        //delete object task
        this.Project.deleteTask(task.TaskInfo.Id);

        //delete div and connecting lines from oData
        if (task.cTaskItem[0]) {
            task.cTaskItem[0].parentNode.removeChild(task.cTaskItem[0]);
        }

        if (this.Chart.isShowDescTask) {
            task.descrTask.parentNode.removeChild(task.descrTask);
        }

        if (task.cTaskItem[1].length > 0) {
            for (var j = 0; j < task.cTaskItem[1].length; j++) {
                task.cTaskItem[1][j].parentNode.removeChild(task.cTaskItem[1][j]);
            }
        }

        //delete div and connecting lines from panelName
        if (task.cTaskNameItem[0]) {
            task.cTaskNameItem[0].parentNode.removeChild(task.cTaskNameItem[0]);
        }

        if (task.cTaskNameItem[1]) {
            for (var j = 0; j < task.cTaskNameItem[1].length; j++) {
                task.cTaskNameItem[1][j].parentNode.removeChild(task.cTaskNameItem[1][j]);
            }
        }

        if (task.cTaskNameItem[2]) {
            task.cTaskNameItem[2].parentNode.removeChild(task.cTaskNameItem[2]);
        }

        //delete object task
        if (task.parentTask)
        {
            if (task.previousChildTask) {
                if (task.nextChildTask) {
                    task.previousChildTask.nextChildTask = task.nextChildTask;
                } else {
                    task.previousChildTask.nextChildTask = null;
                }

            }

            var parentTask = task.parentTask;
            for (var i = 0; i < parentTask.childTask.length; i++)
            {
                if (parentTask.childTask[i].TaskInfo.Id == task.TaskInfo.Id) {
                    parentTask.childTask[i] = null;
                    parentTask.childTask.splice(i, 1);
                    break;
                }
            }
            if (parentTask.childTask.length == 0) {
                if (parentTask.cTaskNameItem[2]) {
                    parentTask.cTaskNameItem[2].parentNode.removeChild(parentTask.cTaskNameItem[2]);
                    parentTask.cTaskNameItem[2] = null;
                }
            }
        } else
        {
            if (task.previousParentTask)
            {
                if (task.nextParentTask) {
                    task.previousParentTask.nextParentTask = task.nextParentTask;
                } else {
                    task.previousParentTask.nextParentTask = null;
                }

            }

            var project = task.Project;
            for (var i = 0; i < project.arrTasks.length; i++) {
                if (project.arrTasks[i].TaskInfo.Id == task.TaskInfo.Id) {
                    project.arrTasks.splice(i, 1);
                }
            }

        }

        if (task.predTask) {
            var predTask = task.predTask;
            for (var i = 0; i < predTask.childPredTask.length; i++) {

                if (predTask.childPredTask[i].TaskInfo.Id == task.TaskInfo.Id) {
                    predTask.childPredTask[i] = null;
                    predTask.childPredTask.splice(i, 1);
                }

            }

        }
        if (task.Project.arrTasks.length != 0) {
            task.Project.shiftProjectItem();
        }
        else {
            task.Project.projectItem[0].style.display = "none";
            if (this.Chart.isShowDescProject) this.hideDescrProject();
        }
        this.Chart._oDataHeight -= 11 + this.Chart.heightTaskItem;
    }

};
/**
 * @desc: Insert the task in the project and returns it
 * @param: id - Specifies id of task
 * @param: name - Specifies name of task
 * @param: EST - Specifies est of task
 * @param: Duration - Specifies duration of task
 * @param: PercentCompleted - Specifies percentCompleted of task
 * @param: predecessorTaskId - Specifies predecessorTask Id of task
 * @type: public
 * @topic: 1
 */
GanttProject.prototype.insertTask = function(id, name, EST, Duration, PercentCompleted, predecessorTaskId, parentTaskId)
{
    var task = null;
    var _task = null;

    if (this.Project.getTaskById(id)) {
        this.Chart.Error.throwError("DATA_INSERT_ERROR", 22, [id]);
        return false;
    }

    if ((!Duration) || (Duration < this.Chart.minWorkLength)) {
        Duration = this.Chart.minWorkLength;
    }
    if ((!name) || (name == "")) {
        name = id;
    }
    if ((!PercentCompleted) || (PercentCompleted == "")) {
        PercentCompleted = 0;

    } else {
        PercentCompleted = parseInt(PercentCompleted);

        if (PercentCompleted < 0 || PercentCompleted > 100) {
            this.Chart.Error.throwError("DATA_INSERT_ERROR", 35, null);
            return false;
        }
    }

    var sortRequired = false;

    if ((parentTaskId) && (parentTaskId != "")) {
        var parentTask = this.Project.getTaskById(parentTaskId);
        if (!parentTask) {
            this.Chart.Error.throwError("DATA_INSERT_ERROR", 21, [parentTaskId]);
            return false;
        }

        EST = EST || parentTask.EST;
        if (EST < parentTask.EST) {
            this.Chart.Error.throwError("DATA_INSERT_ERROR", 20, [id,parentTaskId]);
            return false;
        }

        task = new GanttTaskInfo(id, name, EST, Duration, PercentCompleted, predecessorTaskId);

        if (!this.Chart.checkPosParentTask(parentTask, task)) {
            this.Chart.Error.throwError("DATA_INSERT_ERROR", 19, [parentTaskId,id]);
            return false;
        }
        task.ParentTask = parentTask;

        var _parentTask = this.getTaskById(parentTask.Id);

        var isHide = false;
        if (_parentTask.cTaskItem[0].style.display == "none") {
            isHide = true;
        } else if (_parentTask.cTaskNameItem[2]) {
            if (!_parentTask._isOpen) {
                isHide = true;
            }
        }

        if (isHide) {
            if (_parentTask.childTask.length == 0) {
                this.Chart.openTree(_parentTask.parentTask);
            } else {
                this.Chart.openTree(_parentTask);
            }
        }

        if (predecessorTaskId != "")
        {
            var predTask = this.Project.getTaskById(predecessorTaskId);
            if (!predTask) {
                this.Chart.Error.throwError("DATA_INSERT_ERROR", 27, [predecessorTaskId]);
                return false;
            }

            if (predTask.ParentTask) {
                if (predTask.ParentTask.Id != task.ParentTask.Id) {
                    this.Chart.Error.throwError("DATA_INSERT_ERROR", 32, [predTask.Id,task.Id]);
                    return false;
                }
            } else {
                this.Chart.Error.throwError("DATA_INSERT_ERROR", 32, [predTask.Id,task.Id]);
                return false;
            }

            if (!this.Chart.checkPosPredecessorTask(predTask, task)) {
                this.Chart.correctPosPredecessorTask(predTask, task);
            }

            task.PredecessorTask = predTask;
        }

        var isAdd = false;

        if (sortRequired) for (var i = 0; i < parentTask.ChildTasks.length; i++) {
            if (task.EST < parentTask.ChildTasks[i].EST)
            {
                parentTask.ChildTasks.splice(i, 0, task);
                if (i > 0) {
                    parentTask.ChildTasks[i - 1].nextChildTask = parentTask.ChildTasks[i];
                    parentTask.ChildTasks[i].previousChildTask = parentTask.ChildTasks[i - 1];
                }
                if (parentTask.ChildTasks[i + 1]) {
                    parentTask.ChildTasks[i + 1].previousChildTask = parentTask.ChildTasks[i];
                    parentTask.ChildTasks[i].nextChildTask = parentTask.ChildTasks[i + 1];
                }
                isAdd = true;
                break;
            }
        }

        if (!isAdd) {
            if (parentTask.ChildTasks.length > 0) {
                parentTask.ChildTasks[parentTask.ChildTasks.length - 1].nextChildTask = task;
                task.previousChildTask = parentTask.ChildTasks[parentTask.ChildTasks.length - 1];
            }
            parentTask.ChildTasks.push(task);
        }

        if (parentTask.ChildTasks.length == 1) {
            _parentTask.cTaskNameItem[2] = _parentTask.createTreeImg();
        }

        _task = new GanttTask(task, this, this.Chart);
        _task.create();

        if (task.nextChildTask) _task.nextChildTask = _task.Project.getTaskById(task.nextChildTask.Id);
        _task.addDayInPanelTime();
        _task.shiftCurrentTasks(_task, 23);

    } else
    {

        EST = EST || this.Project.StartDate;

        task = new GanttTaskInfo(id, name, EST, Duration, PercentCompleted, predecessorTaskId);

        if (task.EST <= this.Chart.startDate) {
            this.Chart.Error.throwError("DATA_INSERT_ERROR", 18, [task.Id]);
            return false;
        }

        if (predecessorTaskId != "") {
            var predTask = this.Project.getTaskById(predecessorTaskId);
            if (!predTask) {
                this.Chart.Error.throwError("DATA_INSERT_ERROR", 27, [predecessorTaskId]);
                return false;
            }

            if (!this.Chart.checkPosPredecessorTask(predTask, task)) {
                this.Chart.correctPosPredecessorTask(predTask, task);
            }

            if (predTask.ParentTask) {
                this.Chart.Error.throwError("DATA_INSERT_ERROR", 15, [task.Id,predTask.Id]);
                return false;
            }
            task.PredecessorTask = predTask;
        }
        var isAdd = false;

        if (sortRequired) for (var i = 0; i < this.Project.ParentTasks.length; i++) {

            if (EST < this.Project.ParentTasks[i].EST)
            {
                this.Project.ParentTasks.splice(i, 0, task);
                if (i > 0) {
                    this.Project.ParentTasks[i - 1].nextParentTask = task;
                    task.previousParentTask = this.Project.ParentTasks[i - 1];
                }
                if (this.Project.ParentTasks[i + 1]) {
                    this.Project.ParentTasks[i + 1].previousParentTask = task;
                    task.nextParentTask = this.Project.ParentTasks[i + 1];
                }
                isAdd = true;
                break;
            }
        }

        if (!isAdd) {
            if (this.Project.ParentTasks.length > 0) {
                this.Project.ParentTasks[this.Project.ParentTasks.length - 1].nextParentTask = task;
                task.previousParentTask = this.Project.ParentTasks[this.Project.ParentTasks.length - 1];
            }
            this.Project.ParentTasks.push(task);
        }

        _task = new GanttTask(task, this, this.Chart);
        _task.create();
        if (task.nextParentTask) _task.nextParentTask = _task.Project.getTaskById(task.nextParentTask.Id);
        _task.addDayInPanelTime();

        this.arrTasks.push(_task);
        _task.shiftCurrentTasks(_task, 23);
        this.projectItem[0].style.display = "inline";
        this.setPercentCompleted(this.getPercentCompleted());
        this.shiftProjectItem();

        if (this.Chart.isShowDescProject) {
            this.showDescrProject();
        }

    }

    this.Chart.checkHeighPanelTasks();

    return _task;
};
/**
 * @desc: Check Position of predecessor task
 * @param: predTask  - (object) predecessor task
 * @param: task - (object) current task
 * @type: private
 * @topic: 4
 */
GanttChart.prototype.checkPosPredecessorTask = function(predTask, task)
{
    var widthPred = this.getWidthOnDuration(predTask.Duration);
    var posPred = this.getPosOnDate(predTask.EST);
    var posChild = this.getPosOnDate(task.EST);
    return (widthPred + posPred) <= posChild;

};
GanttChart.prototype.correctPosPredecessorTask = function(predTask, ctask, ctaskObj)
{
    var newDate = new Date(predTask.EST);
    newDate.setHours(newDate.getHours() + (predTask.Duration / this.hoursInDay * 24));
    if (newDate.getHours() > 0) {
        newDate.setHours(0);
        newDate.setDate(newDate.getDate() + 1);
    }

    if (ctaskObj) ctaskObj.setEST(newDate, true);
    else ctask.EST = newDate;

    if (ctask.ParentTask)
    {
        if (!this.checkPosParentTask(ctask.ParentTask, ctask))
        {
            var newDate2 = new Date(ctask.ParentTask.EST);
            newDate2.setHours(newDate2.getHours() + (ctask.ParentTask.Duration / this.hoursInDay * 24));
            ctask.Duration = parseInt((parseInt((newDate2 - ctask.EST) / (1000 * 60 * 60))) * this.hoursInDay / 24);
        }
    }
};
GanttChart.prototype.correctPosParentTask = function(parentTask, ctask)
{
    if (!ctask.PredecessorTask)
    {
        if (parentTask.EST > ctask.EST) {
            ctask.EST = new Date(parentTask.EST);
        }
        if (!this.checkPosParentTask(parentTask, ctask)) {
            ctask.Duration = parentTask.Duration;
        }
    } else
    {
        this.correctPosPredecessorTask(ctask.PredecessorTask, ctask);
    }
};

/**
 * @desc: Check position of parent task
 * @param: parentTask - (object) parent task
 * @type: private
 * @topic: 4
 */
GanttChart.prototype.checkPosParentTaskInTree = function(parentTask)
{
    var isError = false;
    for (var t = 0; t < parentTask.ChildTasks.length; t++)
    {

        if (!this.checkPosParentTask(parentTask, parentTask.ChildTasks[t]))
        {
            if (!this.correctError) {
                this.Error.throwError("DATA_ERROR", 28, [parentTask.Id,parentTask.ChildTasks[t].Id]);
                return true;
            } else {
                this.correctPosParentTask(parentTask, parentTask.ChildTasks[t]);
            }
        }
        if (parentTask.EST > parentTask.ChildTasks[t].EST)
        {
            if (!this.correctError) {
                this.Error.throwError("DATA_ERROR", 33, [parentTask.Id,parentTask.ChildTasks[t].Id]);
                return true;
            } else {
                this.correctPosParentTask(parentTask, parentTask.ChildTasks[t]);
            }
        }

        if (parentTask.ChildTasks[t].ChildTasks.length > 0)
        {
            isError = this.checkPosParentTaskInTree(parentTask.ChildTasks[t]);
        }

    }
    return isError;
};
/**
 * @desc: Set Predecessor Task to child
 * @param: project - (object) current Project
 * @type: private
 * @topic: 0
 */
GanttChart.prototype.setPredTask = function(project)
{
    var isError = false;
    for (var k = 0; k < project.ParentTasks.length; k++) {

        if (!this.isEmpty(project.ParentTasks[k].PredecessorTaskId))
        {
            project.ParentTasks[k].PredecessorTask = project.getTaskById(project.ParentTasks[k].PredecessorTaskId);
            if (!project.ParentTasks[k].PredecessorTask) {
                if (!this.correctError) {
                    this.Error.throwError("DATA_ERROR", 27, [project.ParentTasks[k].PredecessorTaskId]);
                    return true;
                }
            }

            project.ParentTasks[k].PredecessorTask.ChildPredTasks.push(project.ParentTasks[k]);
        }

        if (project.ParentTasks[k].PredecessorTask)
        {
            if (!this.checkPosPredecessorTask(project.ParentTasks[k].PredecessorTask, project.ParentTasks[k])) {
                if (!this.correctError) {
                    this.Error.throwError("DATA_ERROR", 26, [project.ParentTasks[k].PredecessorTask.Id,project.ParentTasks[k].Id]);
                    return true;
                } else {
                    this.correctPosPredecessorTask(project.ParentTasks[k].PredecessorTask, project.ParentTasks[k]);
                }

            }
        }
        isError = this.setPredTaskInTree(project.ParentTasks[k]);
        if (isError) return isError;
    }
    return isError;

};
/**
 * @desc: Set Predecessor Task to child
 * @param: project - (object) current parent task
 * @type: private
 * @topic: 0
 */
GanttChart.prototype.setPredTaskInTree = function(parentTask)
{
    var isError = false;
    for (var t = 0; t < parentTask.ChildTasks.length; t++)
    {
        if (!this.isEmpty(parentTask.ChildTasks[t].PredecessorTaskId))
        {
            parentTask.ChildTasks[t].PredecessorTask = parentTask.Project.getTaskById(parentTask.ChildTasks[t].PredecessorTaskId);
            if (!parentTask.ChildTasks[t].PredecessorTask)
            {
                if (!this.correctError) {
                    this.Error.throwError("DATA_ERROR", 27, [parentTask.ChildTasks[t].PredecessorTaskId]);
                    return true;
                }

            }

            if (!this.checkPosPredecessorTask(parentTask.ChildTasks[t].PredecessorTask, parentTask.ChildTasks[t]))
            {
                if (!this.correctError) {
                    this.Error.throwError("DATA_ERROR", 26, [parentTask.ChildTasks[t].PredecessorTask.Id,parentTask.ChildTasks[t].Id]);
                    return true;
                } else {
                    this.correctPosPredecessorTask(parentTask.ChildTasks[t].PredecessorTask, parentTask.ChildTasks[t]);
                }
            }
            parentTask.ChildTasks[t].PredecessorTask.ChildPredTasks.push(parentTask.ChildTasks[t]);
        }

        if (parentTask.ChildTasks[t].ChildTasks.length > 0)
        {
            isError = this.setPredTaskInTree(parentTask.ChildTasks[t]);
        }

    }
    return isError;
};
/**
 * @desc: Check Position of  Parent Task
 * @param: parentTask - (object) Parent Task
 * @param: task - (object) current Task
 * @type: private
 * @topic: 4
 */
GanttChart.prototype.checkPosParentTask = function(parentTask, task)
{
    var widthParent = this.getWidthOnDuration(parentTask.Duration);
    var posParent = this.getPosOnDate(parentTask.EST);
    var posChild = this.getPosOnDate(task.EST);
    var widthChild = this.getWidthOnDuration(task.Duration);
    return (widthParent + posParent) >= (posChild + widthChild);
};
/**
 * @desc: Insert new GanttProject and returns it
 * @param: id - id of project
 * @param: name - name of project
 * @param: startDate - Start Date of project
 * @type: public
 * @topic: 1
 */
GanttChart.prototype.insertProject = function(id, name, startDate)
{
    if (this._isError)
    {
        this.clearData();
        this.clearItems();
        this.hidePanelErrors();
        this._isError = false;
    }

    if (this.startDate >= startDate) {
        this.Error.throwError("DATA_INSERT_ERROR", 14, null);
        return false;
    }

    if (this.getProjectById(id)) {
        this.Error.throwError("DATA_INSERT_ERROR", 23, [id]);
        return false;
    }

    this.checkHeighPanelTasks();

    var project = new GanttProjectInfo(id, name, startDate);

    this.Project.push(project);

    var _project = new GanttProject(this, project);

    for (var i = 0; i < this.arrProjects.length; i++) {

        if (startDate < this.arrProjects[i].Project.StartDate) {
            this.arrProjects.splice(i, 0, _project);
            if (i > 0) {
                _project.previousProject = this.arrProjects[i - 1];
                this.arrProjects[i - 1].nextProject = _project;
            }
            if (i + 1 <= this.arrProjects.length) {
                _project.nextProject = this.arrProjects[i + 1];
                this.arrProjects[i + 1].previousProject = _project;
                _project.shiftNextProject(_project, 23);
            }
            _project.create();

            if (this.isShowDescProject) {
                _project.hideDescrProject();
            }
            return _project;
        }
    }

    if (this.arrProjects.length > 0) {
        this.arrProjects[this.arrProjects.length - 1].nextProject = _project;
        _project.previousProject = this.arrProjects[this.arrProjects.length - 1];
    }

    this.arrProjects.push(_project);
    _project.create();

    if (this.isShowDescProject) {
        _project.hideDescrProject();
    }

    return _project;
};
/**
 * @desc: show context menu in tree in current position
 * @type: private
 * @topic: 4
 */
GanttChart.prototype._showContextMenu = function(event, obj)
{
    if (this.contextMenu.isDhtmlxMenuObject) {
        var res = this.callEvent("onBeforeContextMenu", [this.contextMenu, obj]);
        if (res === false) return;

        var x, y;
        if (_isIE){
            var dEl0 = window.document.documentElement, dEl1 = window.document.body, corrector = new Array((dEl0.scrollLeft||dEl1.scrollLeft),(dEl0.scrollTop||dEl1.scrollTop));
            x = event.clientX + corrector[0];
            y = event.clientY + corrector[1];
        } else {
            x = event.pageX;
            y = event.pageY;
        }
        this.contextMenu.showContextMenu(x-1, y-1);
    } else {
        var elem = event.srcElement || event.target;
        this.contextMenu.showContextMenu(elem.style.left, elem.style.top, obj);
    }

};
/**
 * @desc: Opens a tree
 * @param: parentTask - (object) parent task
 * @type: private
 * @topic: 3
 */
GanttChart.prototype.openTree = function(parentTask)
{
    var lastParentTask = this.getLastCloseParent(parentTask);
    if (parentTask.TaskInfo.Id != lastParentTask.TaskInfo.Id) {

        this.openNode(lastParentTask);
        this.openTree(parentTask);

    } else {
        this.openNode(lastParentTask);
    }
};
/**
 * @desc: Opens current node
 * @param: parentTask - (object) parent task
 * @type: private
 * @topic: 3
 */
GanttChart.prototype.openNode = function(parentTask)
{
    if (!parentTask._isOpen)
    {
        parentTask.cTaskNameItem[2].src = this.imgs + "minus.gif";
        parentTask._isOpen = true;
        parentTask.shiftCurrentTasks(parentTask, parentTask._heightHideTasks);
        parentTask.showChildTasks(parentTask, parentTask._isOpen);
        parentTask._heightHideTasks = 0;
    }
};
/**
 * @desc: get last close parent
 * @param: task - (object) task
 * @type: private
 * @topic: 2
 */
GanttChart.prototype.getLastCloseParent = function(task)
{
    if (task.parentTask)
    {
        if ((!task.parentTask._isOpen) ||
                (task.parentTask.cTaskNameItem[2].style.display == "none")) {
            return this.getLastCloseParent(task.parentTask);

        } else {
            return task;
        }

    } else {
        return task;
    }
};
/**
 * @desc: create a connection line between this task and predecessor
 * @param: predecessorTaskId - ID of the predecessor Task
 * @type: public
 * @topic: 0
 */
GanttTask.prototype.setPredecessor = function(predecessorTaskId)
{
    if (predecessorTaskId == "") this.clearPredTask();
    else
    {
        var task = this.TaskInfo;
        if (task.Id == predecessorTaskId) {
            this.Chart.Error.throwError("DATA_INSERT_ERROR", 36);
            return false;
        }

        var predTaskObj = this.Project.getTaskById(predecessorTaskId);
        if (!predTaskObj) {
            this.Chart.Error.throwError("DATA_INSERT_ERROR", 27, [predecessorTaskId]);
            return false;
        }
        var predTask = predTaskObj.TaskInfo;
        var a1 = predTask.ParentTask == null, a2 = task.ParentTask == null;
        if (a1 && !a2 || !a1 && a2 || !a1 && !a2 && (predTask.ParentTask.Id != task.ParentTask.Id)) {
            this.Chart.Error.throwError("DATA_INSERT_ERROR", 32, [predTask.Id,task.Id]);
            return false;
        }

        // remove current connection
        this.clearPredTask();

        if (!this.Chart.checkPosPredecessorTask(predTask, task)) {
            this.Chart.correctPosPredecessorTask(predTask, task, this);
        }

        task.PredecessorTaskId = predecessorTaskId;
        task.PredecessorTask = predTask;
        this.predTask = predTaskObj;
        predTaskObj.childPredTask.push(this);

        this.cTaskItem[1] = this.createConnectingLinesDS();
    }
    return true;
};

/**
 *  @desc: remove references and connections to predecessor task
 *  @type: private
 *  @topic: 0
 */
GanttTask.prototype.clearPredTask = function() {
    if (this.predTask) {
        var ch = this.predTask.childPredTask;
        for (var i = 0; i < ch.length; i++) {
            if (ch[i] == this) {
                ch.splice(i, 1);
                break;
            }
        }
        for (var i = 0; i < this.cTaskItem[1].length; i++) {
            this.cTaskItem[1][i].parentNode.removeChild(this.cTaskItem[1][i]);
        }
        this.cTaskItem[1] = [];

        this.TaskInfo.PredecessorTaskId = null;
        this.TaskInfo.PredecessorTask = null;
        this.predTask = null;
    }
};

/**
 * @desc: shifts the task
 * @param: est - est of current Task
 * @param: shiftChild - (true/false) to shift children or not
 * @type: public
 * @topic: 0
 */
GanttTask.prototype.setEST = function(est, shiftChild)
{
    this.moveChild = shiftChild;
    this.getMoveInfo();

    var pos = this.Chart.getPosOnDate(est);
    if ((parseInt(this.cTaskItem[0].firstChild.firstChild.width) + pos > this.maxPosXMove) && (this.maxPosXMove != -1))
    {
        this.Chart.Error.throwError("DATA_INSERT_ERROR", 12, [this.TaskInfo.Id]);
        this.maxPosXMove = -1;
        this.minPosXMove = -1;
        return false;
    }

    if (pos < this.minPosXMove)
    {
        this.Chart.Error.throwError("DATA_INSERT_ERROR", 11, [this.TaskInfo.Id]);
        this.maxPosXMove = -1;
        this.minPosXMove = -1;
        return false;
    }

    this.cTaskItem[0].style.left = pos;

    var width = pos - this.posX;
    this.moveCurrentTaskItem(width, shiftChild);
    this.Project.shiftProjectItem();
    if (this.Chart.isShowDescTask)this.descrTask.innerHTML = this.getDescStr();
    this.addDayInPanelTime();
    this.posX = 0;
    this.maxPosXMove = -1;
    this.minPosXMove = -1;
    return true;
};
/**
 *  @desc: set duration of the current task
 *     @param:  duration - (int) duration of current task in hours
 *  @type: public
 *  @topic: 0
 */
GanttTask.prototype.setDuration = function(duration)
{
    this.getResizeInfo();
    var width = this.Chart.getWidthOnDuration(duration);
    if ((width > this.maxWidthResize) && (this.maxWidthResize != -1))
    {
        this.Chart.Error.throwError("DATA_INSERT_ERROR", 10, [this.TaskInfo.Id]);
        return false;
    } else if (width < this.minWidthResize)
    {
        this.Chart.Error.throwError("DATA_INSERT_ERROR", 9, [this.TaskInfo.Id]);
        return false;
    } else {
        this.taskItemWidth = parseInt(this.cTaskItem[0].firstChild.firstChild.width);
        this.resizeTaskItem(width);
        this.endResizeItem();
        if (this.Chart.isShowDescTask)this.descrTask.innerHTML = this.getDescStr();
        return true;
    }

};
/**
 * @desc: establishes percent completed of the current task
 * @param: percentCompleted - (int) percent completed of current task
 * @type: public
 * @topic: 0
 */
GanttTask.prototype.setPercentCompleted = function(percentCompleted)
{
    percentCompleted = parseInt(percentCompleted);
    if (isNaN(percentCompleted))
    {
        this.Chart.Error.throwError("DATA_INSERT_ERROR", 6, null);
        return false;
    }

    if (percentCompleted > 100)
    {
        this.Chart.Error.throwError("DATA_INSERT_ERROR", 7, null);
        return false;
    }
    if (percentCompleted < 0)
    {
        this.Chart.Error.throwError("DATA_INSERT_ERROR", 8, null);
        return false;
    }

    if ((percentCompleted != 0) && (percentCompleted != 100))
    {
        if ((this.TaskInfo.PercentCompleted != 0) && (this.TaskInfo.PercentCompleted != 100))
        {
            this.cTaskItem[0].childNodes[0].firstChild.rows[0].cells[0].width = percentCompleted + "%";
            this.cTaskItem[0].childNodes[0].firstChild.rows[0].cells[1].width = 100 - percentCompleted + "%";

        } else if ((this.TaskInfo.PercentCompleted == 0) || (this.TaskInfo.PercentCompleted == 100))
        {
            this.cTaskItem[0].childNodes[0].firstChild.rows[0].cells[0].parentNode.removeChild(this.cTaskItem[0].childNodes[0].firstChild.rows[0].cells[0]);

            var cellTblTask = document.createElement("td");
            this.cTaskItem[0].childNodes[0].firstChild.rows[0].appendChild(cellTblTask);
            cellTblTask.height = this.Chart.heightTaskItem + "px";
            cellTblTask.width = percentCompleted + "%";

            var imgPrF = document.createElement("img");
            imgPrF.style.width = (percentCompleted * this.TaskInfo.Duration * this.Chart.hourInPixelsWork) / 100 + "px";
            imgPrF.style.height = this.Chart.heightTaskItem + "px";
            cellTblTask.appendChild(imgPrF);
            imgPrF.src = this.Chart.imgs + "progress_filled.png";

            cellTblTask = document.createElement("td");
            this.cTaskItem[0].childNodes[0].firstChild.rows[0].appendChild(cellTblTask);
            cellTblTask.height = this.Chart.heightTaskItem + "px";
            cellTblTask.width = (100 - percentCompleted) + "%";

            imgPrF = document.createElement("img");
            imgPrF.style.width = ((100 - percentCompleted) * this.TaskInfo.Duration * this.Chart.hourInPixelsWork) / 100 + "px";
            imgPrF.style.height = this.Chart.heightTaskItem + "px";
            cellTblTask.appendChild(imgPrF);
            imgPrF.src = this.Chart.imgs + "progress_bg.png";
        }
    } else if (percentCompleted == 0)
    {
        if ((this.TaskInfo.PercentCompleted != 0) && (this.TaskInfo.PercentCompleted != 100))
        {
            this.cTaskItem[0].childNodes[0].firstChild.rows[0].cells[0].parentNode.removeChild(this.cTaskItem[0].childNodes[0].firstChild.rows[0].cells[0]);
            this.cTaskItem[0].childNodes[0].firstChild.rows[0].cells[0].width = 100 + "%";

        } else
        {
            this.cTaskItem[0].childNodes[0].firstChild.rows[0].cells[0].firstChild.src = this.Chart.imgs + "progress_bg.png";
        }

    } else if (percentCompleted == 100)
    {

        if ((this.TaskInfo.PercentCompleted != 0) && (this.TaskInfo.PercentCompleted != 100))
        {
            this.cTaskItem[0].childNodes[0].firstChild.rows[0].cells[1].parentNode.removeChild(this.cTaskItem[0].childNodes[0].firstChild.rows[0].cells[1]);
            this.cTaskItem[0].childNodes[0].firstChild.rows[0].cells[0].width = 100 + "%";

        } else
        {
            this.cTaskItem[0].childNodes[0].firstChild.rows[0].cells[0].firstChild.src = this.Chart.imgs + "progress_filled.png";
        }
    }

    this.TaskInfo.PercentCompleted = percentCompleted;
    this.taskItemWidth = parseInt(this.cTaskItem[0].firstChild.firstChild.width);
    this.resizeTaskItem(this.taskItemWidth);
    this.endResizeItem();
    if (this.Chart.isShowDescTask)this.descrTask.innerHTML = this.getDescStr();
    return true;
};
/**
 * @desc: set name of the current task
 * @param: name - (string) name of the current task
 * @type: public
 * @topic: 0
 */
GanttTask.prototype.setName = function(name)
{

    if ((name != "") && (name != null)) {
        this.TaskInfo.Name = name;
        if (this.Chart._showTreePanel)
        {
            this.cTaskNameItem[0].innerHTML = name;
            this.cTaskNameItem[0].title = name;
            this.checkWidthTaskNameItem();
        }
        if (this.Chart.isShowDescTask)this.descrTask.innerHTML = this.getDescStr();
        this.addDayInPanelTime();

    }
};
/**
 * @desc: get projectInfo by id
 * @param: id - Project id
 * @type: private
 * @topic: 2
 */
GanttChart.prototype.getProjectInfoById = function(id)
{

    for (var i = 0; i < this.Project.length; i++)
    {
        if (this.Project[i].Id == id)
        {
            return     this.Project[i];
        }
    }
    return null;
};

/**
 * @desc: load xml data from string or file
 * @param: content - (string) XML string or fileName
 * @param: isFile - (true/false) if the content is a file name or XML string. if youload from file, setLoadPath() url is used, fileName is passed in "path" field
 * @param: isLocal - (true/false) if the file is a local file (for debugging purposes) or remote (server-side)
 * @type: public
 * @topic: 6
 */
GanttChart.prototype.loadData = function(content, isFile, isLocal)
{
    this.clearData();

    if ((isFile == null) || (isFile == 'undefined'))
    {
        isFile = false;
    }
    if ((isLocal == null) || (isLocal == 'undefined'))
    {
        isLocal = false;
    }
    this.loadXML(content, isFile, isLocal);

    this.Project.sort(this.sort_byStartDate);
    this.startDate = this.getStartDate();

    this.clearItems();
    //this.panelTime.removeChild(this.panelTime.firstChild);
    //this.panelTime.appendChild(this.createPanelTime());

    for (var i = 0; i < this.Project.length; i++)
    {
        for (var k = 0; k < this.Project[i].ParentTasks.length; k++)
        {
            if ((this.Project[i].ParentTasks[k].EST != null) && (this.Project[i].ParentTasks[k].EST != '')) {
                this.setESTChild(this.Project[i].ParentTasks[k]);
            }
            else {
                this.Error.throwError("DATA_ERROR", 25, [this.Project[i].ParentTasks[k].Id]);
                return;
            }

            if (this.setPredTask(this.Project[i])) return;
        }

        for (var k = 0; k < this.Project[i].ParentTasks.length; k++) {
            if (this.Project[i].ParentTasks[k].EST < this.Project[i].StartDate) {
                this.Error.throwError("DATA_ERROR", 24, [this.Project[i].ParentTasks[k].Id,this.Project[i].Id]);
                return;
            }
            if (this.checkPosParentTaskInTree(this.Project[i].ParentTasks[k])) return;
        }

        this.sortTasksByEST(this.Project[i]);

    }

    for (var i = 0; i < this.Project.length; i++)
    {

        var project = new GanttProject(this, this.Project[i]);

        if (this.arrProjects.length > 0)
        {
            var previousProject = this.arrProjects[this.arrProjects.length - 1];
            project.previousProject = previousProject;
            previousProject.nextProject = project;
        }

        project.create();

        this.checkHeighPanelTasks();
        this.arrProjects.push(project);
        this.createTasks(project);

    }

};

/**
 * @desc: Clearing of a control
 * @type: public
 * @topic: 1
 */
GanttChart.prototype.clearAll = function()
{
    this._oDataHeight = 0;
    this.startDate = null;
    this._isError = false;

    this.hidePanelErrors();
    this.clearData();
    this.clearItems();

};
/**
 * @desc: deleting of a data
 * @type: private
 * @topic: 1
 */
GanttChart.prototype.clearData = function()
{
    this._oDataHeight = 0;
    this.startDate = null;
    this._isError = false;

    this.hidePanelErrors();

    this.Project = [];
    this.arrProjects = [];
};
/**
 * @desc: deleting of items of a control
 * @type: private
 * @topic: 1
 */
GanttChart.prototype.clearItems = function()
{
    this.oData.removeChild(this.oData.firstChild);
    this.oData.appendChild(this.createPanelTasks());
    this.oData.firstChild.appendChild(this.divInfo);
    this.oData.firstChild.appendChild(this.panelErrors);
    if (this._showTreePanel)
    {
        this.panelNames.removeChild(this.panelNames.firstChild);
        this.panelNames.appendChild(this.createPanelNamesTasks());
    }
    this.panelTime.removeChild(this.panelTime.firstChild);
    this.panelTime.appendChild(this.createPanelTime());
};

/**
 * @desc: load xml data
 * @param: content - (string) XML string or fileName
 * @param: isFile - (true/false) if the content is a file name or XML string
 * @param: isLocal - (true/false) if the file is a local file (for debugging purposes) or remote (server-side)
 * @type: private
 * @topic: 6
 */
GanttChart.prototype.loadXML = function(content, isFile, isLocal)
{
    if (isFile && (content == null || content == ""))
    {
        this.Error.throwError("DATA_SEND_ERROR", 4, null);
        return;
    }

    this.xmlLoader = new dtmlXMLLoaderObject(null, this, false);

    try
    {
        if (!isFile)
            try {
                this.xmlLoader.loadXMLString(content);
            } catch (e) {
                this.Error.throwError("DATA_LOAD_ERROR", 37, [content]);
            } else
        if (!isLocal)
        {
            this.xmlLoader.loadXML(this.loadPath + "?path=" + content + "&rnd=" + (new Date() - 0), false);

        } else
        {
            this.xmlLoader.loadXML(content + "?rnd=" + (new Date() - 0), false);
        }
        this.doLoadDetails(isLocal);

    } catch(e)
    {
        this.Error.throwError("DATA_LOAD_ERROR", 5, [content]);
    }

};
/**
 * @desc: parsing of XML data
 * @type: private
 * @topic: 4
 */
GanttChart.prototype.doLoadDetails = function(isLocal)
{
    switch (this.xmlLoader.xmlDoc.status) {
        case 0:
            if (!isLocal)
            {
                this.Error.throwError("DATA_LOAD_ERROR", 1, null);
                return;
            }
            break;
        case 404:
            if (!isLocal)
            {
                this.Error.throwError("DATA_LOAD_ERROR", 5, [this.loadPath]);

            } else
            {
                this.Error.throwError("DATA_LOAD_ERROR", 5, [this.xmlLoader.filePath])
            }
            return;
            break;
        case 500:
            this.Error.throwError("DATA_LOAD_ERROR", 2, null);
            return;
            break;
        default:
            break;
    }

    var name = null;
    var id = null;
    var est = null;
    var duration = null;
    var percentCompleted = null;
    var predecessorTaskId = null;

    //var prArr = [];
    //var tsArr = [];
    //var rootTagProject = this.xmlLoader.getXMLTopNode("projects");
    var projectArr = this.xmlLoader.doXPath("//project");

    for (var j = 0; j < projectArr.length; j++)
    {
        var startDateTemp = projectArr[j].getAttribute("startdate");
        var startDate = startDateTemp.split(",");
        var project = new GanttProjectInfo(projectArr[j].getAttribute("id"), projectArr[j].getAttribute("name"), new Date(startDate[0], (parseInt(startDate[1]) - 1), startDate[2]));

        var taskArr = this.xmlLoader.doXPath("./task", projectArr[j]);

        for (var i = 0; i < taskArr.length; i++) {

            id = taskArr[i].getAttribute("id");
            name = (this.xmlLoader.doXPath("./name", taskArr[i])[0].firstChild == null) ? "" : this.xmlLoader.doXPath("./name", taskArr[i])[0].firstChild.nodeValue;
            var estTemp = (this.xmlLoader.doXPath("./est", taskArr[i])[0].firstChild == null) ? "" : this.xmlLoader.doXPath("./est", taskArr[i])[0].firstChild.nodeValue;
            est = estTemp.split(",");
            duration = (this.xmlLoader.doXPath("./duration", taskArr[i])[0].firstChild == null) ? "" : this.xmlLoader.doXPath("./duration", taskArr[i])[0].firstChild.nodeValue;
            percentCompleted = (this.xmlLoader.doXPath("./percentcompleted", taskArr[i])[0].firstChild == null) ? "" : this.xmlLoader.doXPath("./percentcompleted", taskArr[i])[0].firstChild.nodeValue;
            predecessorTaskId = (this.xmlLoader.doXPath("./predecessortasks", taskArr[i])[0].firstChild == null) ? "" : this.xmlLoader.doXPath("./predecessortasks", taskArr[i])[0].firstChild.nodeValue;

            var task = new GanttTaskInfo(id, name, new Date(est[0], (parseInt(est[1]) - 1), est[2]), duration, percentCompleted, predecessorTaskId);
            var childTasksNode = this.xmlLoader.doXPath("./childtasks", taskArr[i]);
            var childTasksArr = this.xmlLoader.doXPath("./task", childTasksNode[0]);

            if (childTasksArr.length != 0)  this.readChildTasksXML(task, childTasksArr);

            project.addTask(task);

        }

        this.addProject(project);
    }
};
/**
 * @desc: parsing of XML data
 * @param: parentTask  - Parent Task object
 * @param: childTasksArrXML - Array of child tasks (xml)
 * @type: private
 * @topic: 4
 */
GanttChart.prototype.readChildTasksXML = function(parentTask, childTasksArrXML)
{

    var name = null;
    var id = null;
    var est = null;
    var duration = null;
    var percentCompleted = null;
    var predecessorTaskId = null;

    for (var i = 0; i < childTasksArrXML.length; i ++)
    {
        id = childTasksArrXML[i].getAttribute("id");
        name = (this.xmlLoader.doXPath("./name", childTasksArrXML[i])[0].firstChild == null) ? "" : this.xmlLoader.doXPath("./name", childTasksArrXML[i])[0].firstChild.nodeValue;
        var estTemp = (this.xmlLoader.doXPath("./est", childTasksArrXML[i])[0].firstChild == null) ? "" : this.xmlLoader.doXPath("./est", childTasksArrXML[i])[0].firstChild.nodeValue;
        est = estTemp.split(",");
        duration = (this.xmlLoader.doXPath("./duration", childTasksArrXML[i])[0].firstChild == null) ? "" : this.xmlLoader.doXPath("./duration", childTasksArrXML[i])[0].firstChild.nodeValue;
        percentCompleted = (this.xmlLoader.doXPath("./percentcompleted", childTasksArrXML[i])[0].firstChild == null) ? "" : this.xmlLoader.doXPath("./percentcompleted", childTasksArrXML[i])[0].firstChild.nodeValue;
        predecessorTaskId = (this.xmlLoader.doXPath("./predecessortasks", childTasksArrXML[i])[0].firstChild == null) ? "" : this.xmlLoader.doXPath("./predecessortasks", childTasksArrXML[i])[0].firstChild.nodeValue;
        var task = new GanttTaskInfo(id, name, new Date(est[0], (parseInt(est[1]) - 1), est[2]), duration, percentCompleted, predecessorTaskId);
        task.ParentTask = parentTask;

        parentTask.addChildTask(task);

        var childTasksNode = this.xmlLoader.doXPath("./childtasks", childTasksArrXML[i]);
        var childTasksArr = this.xmlLoader.doXPath("./task", childTasksNode[0]);
        if (childTasksArr.length != 0)
        {
            this.readChildTasksXML(task, childTasksArr);
        }

    }

};
/**
 * @desc: create XML string from the chart content
 * @type: public
 * @topic: 6
 */
GanttChart.prototype.getXML = function()
{
    var strXML = "<projects>";

    for (var i = 0; i < this.Project.length; i++)
    {
        strXML += "<project id ='" + this.Project[i].Id + "' name= '" + this.Project[i].Name + "' startdate = '" + this.Project[i].StartDate.getFullYear() + "," + (this.Project[i].StartDate.getMonth() + 1) + "," + this.Project[i].StartDate.getDate() + "'>";

        for (var j = 0; j < this.Project[i].ParentTasks.length; j++)
        {
            strXML += "<task id ='" + this.Project[i].ParentTasks[j].Id + "'>";
            strXML += "<name>" + this.Project[i].ParentTasks[j].Name + "</name>";
            strXML += "<est>" + this.Project[i].ParentTasks[j].EST.getFullYear() + "," + (this.Project[i].ParentTasks[j].EST.getMonth() + 1) + "," + this.Project[i].ParentTasks[j].EST.getDate() + "</est>";
            strXML += "<duration>" + this.Project[i].ParentTasks[j].Duration + "</duration>";
            strXML += "<percentcompleted>" + this.Project[i].ParentTasks[j].PercentCompleted + "</percentcompleted>";
            strXML += "<predecessortasks>" + this.Project[i].ParentTasks[j].PredecessorTaskId + "</predecessortasks>";
            strXML += "<childtasks>";
            strXML += this.createChildTasksXML(this.Project[i].ParentTasks[j].ChildTasks);
            strXML += "</childtasks>";
            strXML += "</task>";

        }

        strXML += "</project>";

    }
    strXML += "</projects>";
    return strXML;

};
/**
 * @desc: create XML
 * @type: private
 * @topic: 4
 */
GanttChart.prototype.createChildTasksXML = function(childTasks)
{
    var strXML = "";
    for (var n = 0; n < childTasks.length; n++)
    {
        strXML += "<task id='" + childTasks[n].Id + "'>";
        strXML += "<name>" + childTasks[n].Name + "</name>";
        strXML += "<est>" + childTasks[n].EST.getFullYear() + "," + (childTasks[n].EST.getMonth() + 1) + "," + childTasks[n].EST.getDate() + "</est>";
        strXML += "<duration>" + childTasks[n].Duration + "</duration>";
        strXML += "<percentcompleted>" + childTasks[n].PercentCompleted + "</percentcompleted>";
        strXML += "<predecessortasks>" + childTasks[n].PredecessorTaskId + "</predecessortasks>";
        if (childTasks[n].ChildTasks)
        {
            strXML += "<childtasks>";
            strXML += this.createChildTasksXML(childTasks[n].ChildTasks);
            strXML += "</childtasks>";
        }
        strXML += "</task>";
    }
    return strXML;

};
/**
 * @desc: function of sorting by EST
 * @type: private
 * @topic: 4
 */
GanttChart.prototype.sort_byEST = function(a, b)
{
    if (a.EST < b.EST) return -1;
    if (a.EST > b.EST) return 1;
    return 0;
};
/**
 * @desc: function of sorting by start date
 * @type: private
 * @topic: 4
 */
GanttChart.prototype.sort_byStartDate = function(a, b)
{
    if (a["StartDate"] < b["StartDate"]) return -1;
    if (a["StartDate"] > b["StartDate"]) return 1;
    return 0;
};

/**
 * @desc: set the date to child tasks
 * @param: parentTask  - (object) parent task
 * @type: private
 * @topic: 4
 */
GanttChart.prototype.setESTChild = function(parentTask)
{
    for (var t = 0; t < parentTask.ChildTasks.length; t++)
    {
        if ((parentTask.ChildTasks[t].EST == null ) || (parentTask.ChildTasks[t].EST == ""))
        {
            parentTask.ChildTasks[t].EST = parentTask.EST;
        }

        if (parentTask.ChildTasks[t].ChildTasks.length != 0) this.setESTChild(parentTask.ChildTasks[t]);
    }

};

/**
 * @desc: creation of the panel containing tasks
 * @type: private
 * @topic: 4
 */
GanttChart.prototype.createPanelTasks = function()
{
    var divTasks = document.createElement("div");
    divTasks.className = "taskPanel";
    divTasks.style.cssText = "position:relative;";
    divTasks.style.height = this.contentHeight - 63 + "px";
    var w = this.startDate ? (this.startDate.getDay()-1) : ((new Date(0)).getDay()-1);
    if (w==-1) w=6;
    divTasks.style.background = "url(" + this.imgs + "bg_week.png) -"+(w*24)+"px 0px";
    this.panelTasks = divTasks;
    return divTasks;
};
/**
 * @desc: creation of the panel containing names of tasks
 * @type: private
 * @topic: 4
 */
GanttChart.prototype.createPanelNamesTasks = function()
{
    var divListNames = document.createElement("div");
    divListNames.innerHTML = "&nbsp;";
    divListNames.style.cssText = "position:relative;background:url(" + this.imgs + "bg.png)";
    divListNames.style.height = this.contentHeight - 63 + "px";
    divListNames.style.width = this.maxWidthPanelNames + "px";

    return divListNames;
};
/**
 * @desc: creation a window with the data of task
 * @type: private
 * @topic: 4
 */
GanttChart.prototype.createPopUpInfo = function()
{
    var divTaskInfo = document.createElement("div");
    divTaskInfo.style.cssText = 'display: none;';

    var tblTaskInfo = document.createElement("table");
    tblTaskInfo.style.cssText = "position:absolute;top:0px;left:0px";
    tblTaskInfo.className = "poPupInfo";
    divTaskInfo.appendChild(tblTaskInfo);

    var rowTaskInfo = tblTaskInfo.insertRow(tblTaskInfo.rows.length);
    var cellTaskInfo = document.createElement("td");
    rowTaskInfo.appendChild(cellTaskInfo);
    this.divInfo = divTaskInfo;
    
    return divTaskInfo;
};
/**
 * @desc: creation a window with the current date
 * @type: private
 * @topic: 4
 */
GanttChart.prototype.createPopUpTimeInfo = function()
{
    var divTimeInfo = document.createElement("div");
    divTimeInfo.style.display = "none";

    var tblTimeInfo = document.createElement("table");
    tblTimeInfo.className = "poPupTime";
    divTimeInfo.appendChild(tblTimeInfo);

    var rowTimeInfo = tblTimeInfo.insertRow(tblTimeInfo.rows.length);
    var cellTimeInfo = document.createElement("td");
    cellTimeInfo.align = "center";
    rowTimeInfo.appendChild(cellTimeInfo);

    return divTimeInfo;
};
/**
 * @desc: create a panel with the days
 * @type: private
 * @topic: 4
 */
GanttChart.prototype.createPanelTime = function()
{
    var panelTime = document.createElement("div");
    panelTime.style.position = "relative";

    var tblTime = document.createElement("table");
    panelTime.appendChild(tblTime);
    tblTime.cellPadding = "0px";
    tblTime.border = "0px";
    tblTime.cellSpacing = "0px";
    tblTime.bgColor = "#FFFFFF";
    tblTime.style.marginTop = "0px";

    var monthRow = tblTime.insertRow(tblTime.rows.length);

    var newRow = tblTime.insertRow(tblTime.rows.length);

    //creating cells for tblTime
    for (var i = 0; i < this.countDays; i++)
    {
        this.addPointInTimePanel(newRow, panelTime);
        this.addDayInPanelTime(newRow);
    }

    return  panelTime;
};
/**
 * @desc: creation of point in panel time
 * @param: row - current row
 * @param: panelTime -Panel which contains days
 * @type: private
 * @topic: 4
 */
GanttChart.prototype.addPointInTimePanel = function(row, panelTime)
{
    var leftLine = document.createElement("div");
    leftLine.style.cssText = "position:absolute;left:" + ( row.cells.length * this.dayInPixels ) + "px;top:20px;height:20px;width:1px;font-size:1px;margin-left:0px;margin-right:0px;margin-top:0px;margin-bottom:0px;background:#f1f3f1;";
    panelTime.appendChild(leftLine);
};
GanttChart.prototype._calculateMonthColSpan = function(date, maxLen) {
    var m1 = date.getMonth();
    for(var i=1; i<=maxLen; i++) {
        date.setDate(date.getDate() + 1);
        var m2 = date.getMonth();
        if (m2 != m1) return i;
    }
    return maxLen;
};
/**
 * @desc: Returns a string representation of current month for the month scale row. You may override this function to customize the label.
 * @param: date - {JavaScript Date object}, the date of month for which you should render month label.
 * @type: public, overridable
 * @topic: 3
 */
GanttChart.prototype.getMonthScaleLabel = function(date) {
    return (this._useShortMonthNames ? this.shortMonthNames : this.monthNames)[date.getMonth()] + " '" + (""+date.getFullYear()).substring(2);
};
/**
 * @desc: Use short or full month name in the month label axis. Default is true.
 * @param: flag - {true|false}
 * @type: public
 * @topic: 3
 * @before_init: 1
 */
GanttChart.prototype.useShortMonthNames = function(flag) {
    this._useShortMonthNames = flag;
};
/**
 * @desc: Define short month names for your locale
 * @param: names - an array of strings, ["Jan", "Feb", ...]
 * @type: public
 * @topic: 3
 * @before_init: 1
 */
GanttChart.prototype.setShortMonthNames = function(names) {
    this.shortMonthNames = names;
};
/**
 * @desc: Define full month names for your locale
 * @param: names - an array of strings, ["January", "February", ...]
 * @type: public
 * @topic: 3
 * @before_init: 1
 */
GanttChart.prototype.setMonthNames = function(names) {
    this.monthNames = names;
};
/**
 * @desc: Add day in panel time
 * @param: row - row, which contains days
 * @type: private
 * @topic: 4
 */
GanttChart.prototype.addDayInPanelTime = function(row)
{
    var self = this, idx = row.cells.length, date = new Date(this.startDate);

    var newCell = row.insertCell(idx);
    newCell.style.height = "20px";
    newCell.style.width = this.dayInPixels + "px";
    newCell.className = "dayNumber";

    date.setDate(date.getDate() + parseInt(idx));
    var day = date.getDate()
    newCell.innerHTML = day;
    newCell.setAttribute("idx", idx);

    var monthRow = row.parentNode.parentNode.rows[0];
    if (idx==0 || day==1) {
        var newCell2 = monthRow.insertCell(monthRow.cells.length);
        newCell2.className = "monthName";
        newCell2.style.height = "20px";
        if (monthRow.cells.length%2 == 0) newCell2.style.backgroundColor = "#f7f8f7";
        newCell2.colSpan = this._calculateMonthColSpan(new Date(date), Math.max(1,this.countDays-idx));
        newCell2.innerHTML = this.getMonthScaleLabel(date);
    } else {
        var n = monthRow.cells.length, cs=0;
        for(var i=0; i<n; i++){
            cs += monthRow.cells[i].colSpan;
        }
        if (idx>=cs) monthRow.cells[n-1].colSpan += 1; 
    }

    var w = date.getDay();
    if (w==0 || w==6) newCell.style.backgroundColor = "#f7f8f7";
};
/**
 * @desc: increment Height of Panel Tasks
 * @type: private
 * @topic: 4
 */
GanttChart.prototype.incHeightPanelTasks = function(height)
{
    var containerTasks = this.oData.firstChild;
    containerTasks.style.height = parseInt(containerTasks.style.height) + height + "px";
};
/**
 * @desc: increment Height of Panel Names
 * @type: private
 * @topic: 4
 */
GanttChart.prototype.incHeightPanelNames = function(height)
{
    var containerNames = this.panelNames.firstChild;
    containerNames.style.height = parseInt(containerNames.style.height) + height + "px";
};
/**
 * @desc: check Heigh of Panel Tasks
 * @type: private
 * @topic: 4
 */
GanttChart.prototype.checkHeighPanelTasks = function()
{
    this._oDataHeight += 11 + this.heightTaskItem;
    if ((parseInt(this.oData.firstChild.style.height) <= this._oDataHeight)) {
        this.incHeightPanelTasks(this.heightTaskItem + 11);
        if (this._showTreePanel) this.incHeightPanelNames(this.heightTaskItem + 11);
    }
};
/**
 * @desc: sorting of tasks by EST in the current project
 * @param: project - current project
 * @type: private
 * @topic: 4
 */
GanttChart.prototype.sortTasksByEST = function(project)
{
    project.ParentTasks.sort(this.sort_byEST);

    for (var i = 0; i < project.ParentTasks.length; i++)
    {
        project.ParentTasks[i] = this.sortChildTasks(project.ParentTasks[i]);
    }

};
/**
 * @desc: sorting of child tasks in the parent task
 * @param: parenttask  - (object) parent task
 * @type: private
 * @topic: 4
 */
GanttChart.prototype.sortChildTasks = function(parenttask)
{
    parenttask.ChildTasks.sort(this.sort_byEST);

    for (var i = 0; i < parenttask.ChildTasks.length; i++)
    {
        if (parenttask.ChildTasks[i].ChildTasks.length > 0) this.sortChildTasks(parenttask.ChildTasks[i]);
    }
    return parenttask;
};
/**
 * @desc: Handler of data errors
 * @param: type - type of error
 * @param: descr - description of error
 * @param: params - current data
 * @type: private
 * @topic: 5
 */
GanttChart.prototype.errorDataHandler = function(type, descr, params)
{
    if (!this._isError)
    {
        this.clearData();
        this.showPanelErrors();
        this._isError = true;
    }
    this.addErrorInPanelErrors(type, descr);
};
/**
 * @desc: creation of Panel Errors
 * @type: private
 * @topic: 4
 */
GanttChart.prototype.createPanelErrors = function()
{
    var tbl = document.createElement("table");
    tbl.width = "100%";
    tbl.style.display = "none";
    tbl.className = "panelErrors";
    this.panelErrors = tbl;

    return tbl;

};
/**
 * @desc: show of Panel Errors
 * @type: private
 * @topic: 4
 */
GanttChart.prototype.showPanelErrors = function()
{
    this.panelErrors.style.display = "inline";
};
/**
 * @desc: hide of Panel Errors
 * @type: private
 * @topic: 4
 */
GanttChart.prototype.hidePanelErrors = function()
{
    for (var i = 0; i < this.panelErrors.rows.length; i++) {

        this.panelErrors.rows[i].parentNode.removeChild(this.panelErrors.rows[i]);
    }
    this.panelErrors.style.display = "none";
};
/**
 * @desc: add error message in Panel Errors
 * @type: private
 * @topic: 4
 */
GanttChart.prototype.addErrorInPanelErrors = function(type, descr)
{
    var row = this.panelErrors.insertRow(this.panelErrors.rows.length);
    var cell = document.createElement("td");
    cell.style.height = "20px";
    cell.style.width = "100px";
    cell.innerHTML = type;
    row.appendChild(cell);

    cell = document.createElement("td");
    row.appendChild(cell);
    cell.innerHTML = descr;
};
/**
 * @desc: Handler of  errors
 * @param: type - type of error
 * @param: descr - description of error
 * @param: params - current data
 * @type: private
 * @topic: 5
 */
GanttChart.prototype.errorSendDataHandler = function(type, descr, params)
{
    alert(descr);
};
/**
 * @desc: Handler of errors
 * @param: type - type of error
 * @param: descr - description of error
 * @param: params - current data
 * @type: private
 * @topic: 5
 */
GanttChart.prototype.errorLoadDataHandler = function(type, descr, params)
{
    alert(descr);
};
/**
 * @desc: Handler of API errors
 * @param: type - type of error
 * @param: descr - description of error
 * @param: params - current data
 * @type: private
 * @topic: 5
 */
GanttChart.prototype.errorAPIHandler = function(type, descr, params)
{
    alert(descr);
};
/**
 * @desc: saves data to server, using setSavePath() url and "application/x-www-form-urlencoded" encoding
 * @param: fileName - passed to server as "filename" field, xml content is passed in "data" field
 * @type: public
 * @topic: 6
 */
GanttChart.prototype.saveData = function(fileName)
{
    try {

        if (!this.dhtmlXMLSenderObject.isProcessed)
        {
            this.dhtmlXMLSenderObject.sendData(fileName, this.savePath, this.getXML());
        }

    } catch (e) {
        this.Error.throwError("DATA_SEND_ERROR", e, null);
    }
};
/**
 * @desc: creation of GanttChart
 * @param: divId - id of div in which the control lays
 * @param: xmlFile - path to XML document
 * @type: public
 * @topic: 0
 */
GanttChart.prototype.create = function(divId)
{
    var self = this;
    var content = document.getElementById(divId);
    this.content = content;
    this.getBrowserType();

    //
    if (this._isIE) {
        document.body.attachEvent('onselectstart', function() {
            window.event.returnValue = false;
        });

        document.body.attachEvent('onkeydown', function() {
            if (event.keyCode == 65 && event.ctrlKey) window.event.returnValue = false;
        });

    } else {
        content.addEventListener('mousedown', function(e) {
            e.preventDefault();
        }, true);
        document.addEventListener('keydown', function(e) {
            if (e.keyCode == 65 && e.ctrlKey) e.preventDefault();
        }, true);
    }

    //init handlers
    this.Error.catchError("DATA_ERROR", function(type, descr, params) {
        self.errorDataHandler(type, descr, params)
    });
    this.Error.catchError("DATA_SEND_ERROR", function(type, descr, params) {
        self.errorSendDataHandler(type, descr, params)
    });
    this.Error.catchError("DATA_INSERT_ERROR", function(type, descr, params) {
        self.errorAPIHandler(type, descr, params)
    });
    this.Error.catchError("DATA_LOAD_ERROR", function(type, descr, params) {
        self.errorLoadDataHandler(type, descr, params)
    });

    //create Table
    var tableControl = document.createElement("table");
    tableControl.cellPadding = "0";
    tableControl.cellSpacing = "0";
    tableControl.style.cssText = "width: 100%; position: relative;";
    var newRowTblControl = tableControl.insertRow(tableControl.rows.length);
    var newCellTblControl;

    //Add to content Table
    this.contentHeight = content.offsetHeight;
    this.contentWidth = content.offsetWidth;
    content.appendChild(tableControl);

    this.countDays = this.getCountDays();

    this.Project.sort(this.sort_byStartDate);
    this.startDate = this.getStartDate();

    //Creation panel of time
    this.panelTime = document.createElement("div");
    this.panelTime.appendChild(this.createPanelTime());
    this.panelTime.style.cssText = "position:relative;overflow:hidden;height:40px;top:0px;left:1px";

    //Creation panel oData
    this.oData = document.createElement("div");
    this.oData.appendChild(this.createPanelTasks());
    this.oData.style.cssText = "position:relative;overflow:scroll;height:" + (this.contentHeight - 40) + "px;border-left:#f1f3f1 1px solid";

    this.oData.firstChild.appendChild(this.createPanelErrors());

    //Creation panel of names
    if (this._showTreePanel)
    {
        this.panelNames = document.createElement("div");
        newCellTblControl = document.createElement("td");
        newCellTblControl.vAlign = "top";

        this.panelNames.appendChild(this.createPanelNamesTasks());
        this.panelNames.style.cssText = "position:relative;top:40px;overflow:hidden;border-left:#f1f3f1 1px solid;border-bottom:#f1f3f1 1px solid";
        newCellTblControl.appendChild(this.panelNames);
        newRowTblControl.appendChild(newCellTblControl);
    }

    //add oData and oDataTime
    newCellTblControl = document.createElement("td");
    var divCell = document.createElement("div");
    divCell.style.cssText = "position: relative;";
    divCell.appendChild(this.panelTime);
    divCell.appendChild(this.oData);
    newCellTblControl.appendChild(divCell);
    newRowTblControl.appendChild(newCellTblControl);

    //Show panel of names
    if (this._showTreePanel) {
        this.panelNames.style.height = (this.contentHeight - 56) + "px";
        this.panelNames.style.width = this.maxWidthPanelNames + "px";
        this.oData.style.width = (this.contentWidth - this.maxWidthPanelNames) + "px";
        this.panelTasks.style.width = this.dayInPixels * this.countDays + "px";
        this.panelTime.style.width = (this.contentWidth - this.maxWidthPanelNames - 0*18) + "px";
        this.panelTime.firstChild.style.width = this.dayInPixels * this.countDays + "px";
        if (this.isShowConMenu && this.contextMenu == null) this.contextMenu = new contextMenu(this);
    } else {
        this.oData.style.width = this.contentWidth + "px";
        this.panelTime.style.width = (this.contentWidth - 16) + "px";
    }

    if (this._isOpera) {
        this.oData.onmousewheel = function() {
            return false;
        }
    }

    this.oData.onscroll = function() {
        self.panelTime.scrollLeft = this.scrollLeft;

        if (self.panelNames) {
            self.panelNames.scrollTop = this.scrollTop;
            if (self.isShowConMenu) self.contextMenu.hideContextMenu();
        }

    };

    //create pop up time info
    this.divTimeInfo = this.createPopUpTimeInfo();
    divCell.appendChild(this.divTimeInfo);

    //create pop up info task
    this.oData.firstChild.appendChild(this.createPopUpInfo());

    //this.Project.sort(this.sort_byStartDate);
    //this.startDate = this.getStartDate();

    for (var i = 0; i < this.Project.length; i++)
    {

        for (var k = 0; k < this.Project[i].ParentTasks.length; k++)
        {
            if (this.isEmpty(this.Project[i].ParentTasks[k].EST)) {
                this.Project[i].ParentTasks[k].EST = this.Project[i].StartDate;
            }
            this.setESTChild(this.Project[i].ParentTasks[k]);

            if (this.setPredTask(this.Project[i])) return;
        }

        for (var k = 0; k < this.Project[i].ParentTasks.length; k++) {
            if (this.Project[i].ParentTasks[k].EST < this.Project[i].StartDate) {

                if (!this.correctError) {
                    this.Error.throwError("DATA_ERROR", 24, [this.Project[i].ParentTasks[k].Id,this.Project[i].Id]);
                    return;
                } else {
                    this.Project[i].ParentTasks[k].EST = this.Project[i].StartDate;
                }
            }
            if (this.checkPosParentTaskInTree(this.Project[i].ParentTasks[k])) return;
        }

        this.sortTasksByEST(this.Project[i]);

    }

    for (var i = 0; i < this.Project.length; i++)
    {
        //creation project
        var project = new GanttProject(this, this.Project[i]);

        if (this.arrProjects.length > 0)
        {
            var previousProject = this.arrProjects[this.arrProjects.length - 1];
            project.previousProject = previousProject;
            previousProject.nextProject = project;
        }
        project.create();

        this.checkHeighPanelTasks();
        this.arrProjects.push(project);
        this.createTasks(project);

    }

    return this;
};

GanttChart.prototype.isEmpty = function(value)
{
    return (value == null || value == '');
};

/**
 * @desc: returns chart in html format suitable for printing, full-sized and without scrollbars
 * @type: public
 * @topic: 7
 */
GanttChart.prototype.getPrintableHTML = function()
{
    var w = parseInt(this.oData.firstChild.style.width) - parseInt(this.oData.style.width);
    var h = parseInt(this.panelTasks.style.height) - parseInt(this.panelTasks.parentNode.style.height);

    this.oData.setAttribute("id","ganttPrint02");
    this.panelNames.setAttribute("id","ganttPrint03");

    var res = '<html><head><link type="text/css" rel="stylesheet" href="'+this.stylePath+'"><scr'+'ipt>onload=function(){var w=' + w + ',h=' + h +
            ',c1=document.getElementById("ganttPrint01"),c2=document.getElementById("ganttPrint02"),c3=document.getElementById("ganttPrint03");' +
            'c2.style.width=parseInt(c2.style.width)+w+"px";c2.previousSibling.style.width=c2.style.width;c1.style.width=parseInt(c1.style.width)+w+"px";c2.style.height=parseInt(c2.style.height)+h+"px";' +
            'c2.style.overflow="hidden";c3.style.height=c3.firstChild.style.height;c1.style.height=parseInt(c1.style.height)+h+"px";}</scr'+'ipt></head>' +
            '<body><div id="ganttPrint01" style="' + this.content.style.cssText + '">' + this.content.innerHTML + '</div></body></html>';

    this.oData.setAttribute("id",null);
    this.panelNames.setAttribute("id",null);

    return res;
};

/**
 * @desc: opens chart in a new window, from where you can print it as you like - you can use browser's "Print preview" menu button to layout the chart on your page, choose a paper size etc.
 * @param: message - (string) this message will appear in alert window to instruct user what to do for printing. Set it to null to skip this alert. By default it says "Use browser's menu File->Print preview to setup page layout."
 * @type: public
 * @topic: 7
 */
GanttChart.prototype.printToWindow = function(message)
{
    var o = window.open();
    o.document.write(this.getPrintableHTML());
    o.document.close();
    if (message!==null) {
        o.alert(message ? message : "Use browser's menu \"File->Print preview\" to setup page layout." );
    }
};

/**
 * @desc: Calculation of Start Date
 * @type: private
 * @topic: 4
 */
GanttChart.prototype.getStartDate = function()
{
    for (var i = 0; i < this.Project.length; i++) {

        if (this.startDate) {
            if (this.Project[i].StartDate < this.startDate) {
                this.startDate = new Date(this.Project[i].StartDate);
            }
        }
        else {
            this.startDate = new Date(this.Project[i].StartDate);
        }
    }

    this.initialPos = 24 * this.hourInPixels;
    if (this.startDate) {
        return new Date(this.startDate.setHours(this.startDate.getHours() - 24));
    }
    else {
        return new Date();
    }

};
/**
 * @desc: Calculation of Count Days
 * @type: private
 * @topic: 4
 */
GanttChart.prototype.getCountDays = function()
{

    if (this._showTreePanel) {
        return parseInt((this.contentWidth - this.maxWidthPanelNames) / (this.hourInPixels * 24));

    } else {
        return parseInt((this.contentWidth) / (this.hourInPixels * 24));
    }

};
/**
 * @desc: Creation of tasks
 * @param: project - (object)project
 * @type: private
 * @topic: 4
 */
GanttChart.prototype.createTasks = function(project)
{
    for (var j = 0; j < project.Project.ParentTasks.length; j++)
    {
        if (j > 0)
        {
            project.Project.ParentTasks[j - 1].nextParentTask = project.Project.ParentTasks[j];
            project.Project.ParentTasks[j].previousParentTask = project.Project.ParentTasks[j - 1];
        }

        var task = new GanttTask(project.Project.ParentTasks[j], project, this);
        project.arrTasks.push(task);
        task.create();

        this.checkHeighPanelTasks();

        if (project.Project.ParentTasks[j].ChildTasks.length > 0)
        {
            this.createChildItemControls(project.Project.ParentTasks[j].ChildTasks, project);
        }
    }
};
/**
 * @desc: Creation of tasks
 * @param: arrChildTasks - array of child tasks
 * @param: project - (object)project
 * @type: private
 * @topic: 4
 */
GanttChart.prototype.createChildItemControls = function(arrChildTasks, project)
{
    for (var i = 0; i < arrChildTasks.length; i++) {

        if (i > 0)
        {
            arrChildTasks[i].previousChildTask = arrChildTasks[i - 1];
            arrChildTasks[i - 1].nextChildTask = arrChildTasks[i];
        }
        var task = new GanttTask(arrChildTasks[i], project, this);
        task.create();

        this.checkHeighPanelTasks();

        if (arrChildTasks[i].ChildTasks.length > 0)
        {
            this.createChildItemControls(arrChildTasks[i].ChildTasks, project);
        }
    }

};
/**
 * @desc: show a small window with the data of task
 * @param: event - (object)event
 * @type: private
 * @topic: 4
 */
GanttTask.prototype.getPopUpInfo = function(object, event)
{
    //this.cTaskItem[0]
    var posY = object.offsetTop + this.Chart.heightTaskItem + 6;
    var posX = object.offsetLeft + ((event.layerX == null) ? event.offsetX : event.layerX);

    //data of task
    var tblInfo = this.Chart.divInfo.lastChild;
    tblInfo.rows[0].cells[0].innerHTML = "<div style='font-family: Arial, Helvetica, Sans-serif; font-size: 12px; font-weight: bold; color: #688060; margin: 0 0 4px 0;'>" + this.TaskInfo.Name + "</div>";
    tblInfo.rows[0].cells[0].innerHTML += "<span class='st'>EST:&nbsp;</span><span class='ut'>" + this.TaskInfo.EST.getDate() + "." + (this.TaskInfo.EST.getMonth() + 1) + "." + this.TaskInfo.EST.getFullYear() + "</span><br/>";
    tblInfo.rows[0].cells[0].innerHTML += "<span class='st'>Duration:&nbsp;</span><span class='ut'>" + this.TaskInfo.Duration + " hours </span><br/>";
    tblInfo.rows[0].cells[0].innerHTML += "<span class='st'>Percent Complete:&nbsp;</span><span class='ut'>" + this.TaskInfo.PercentCompleted + "% </span><br/>";

    //show predecessor task
    if (this.predTask)
    {
        tblInfo.rows[0].cells[0].innerHTML += "<span class='st'>Predecessor Task:&nbsp;</span>";
        tblInfo.rows[0].cells[0].innerHTML += "<span class='lt'>*" + this.TaskInfo.PredecessorTask.Name + "</span>";
    }

    //show child tasks
    if (this.TaskInfo.ChildTasks.length != 0) {
        tblInfo.rows[0].cells[0].innerHTML += "<span class='st'>Child Tasks:&nbsp;</span>";
        for (var i = 0; i < this.TaskInfo.ChildTasks.length; i++)
        {
            tblInfo.rows[0].cells[0].innerHTML += (i == this.TaskInfo.ChildTasks.length - 1) ? ("<span class='lt'>*" + this.TaskInfo.ChildTasks[i].Name + "</span>") : ("<span class='lt'>*" + this.TaskInfo.ChildTasks[i].Name + "</span>");
        }
    }

    //show parent task
    if (this.TaskInfo.ParentTask) {
        tblInfo.rows[0].cells[0].innerHTML += "<span class='st'>Parent Task:&nbsp;</span>";
        tblInfo.rows[0].cells[0].innerHTML += "<span class='lt'>*" + this.TaskInfo.ParentTask.Name + "</span>";
    }

    this.Chart.divInfo.style.cssText = "z-index:2;position: absolute;display: inline;";

    if (posY + this.Chart.divInfo.lastChild.offsetHeight + 10 > this.Chart.oData.offsetHeight + this.Chart.oData.scrollTop) {
        this.Chart.divInfo.style.top = (posY - this.Chart.divInfo.lastChild.offsetHeight - 10 - this.Chart.heightTaskItem) + "px";
    }
    else {
        this.Chart.divInfo.style.top = posY + "px";
    }

    if (this.Chart.divInfo.lastChild.offsetWidth + posX + 10 > this.Chart.oData.offsetWidth + this.Chart.oData.scrollLeft) {
        this.Chart.divInfo.style.left = posX - (this.Chart.divInfo.lastChild.offsetWidth + posX + 20 - (this.Chart.oData.offsetWidth + this.Chart.oData.scrollLeft)) + "px";

    } else {
        this.Chart.divInfo.style.left = posX + "px";
    }

};
/**
 * @desc: close a window in browser with the data of task
 * @type: private
 * @topic: 4
 */
GanttTask.prototype.closePopUpInfo = function()
{
    this.Chart.divInfo.style.display = "none";
};
/**
 * @desc: creation  connecting lines in panel of names
 * @type: private
 * @topic: 4
 */
GanttTask.prototype.createConnectingLinesPN = function()
{
    var arrConnectingLinesNames = [];

    /*var lineVerticalLeft = document.createElement("div");
    lineVerticalLeft.style.cssText = "border-width: 0px 0px 0px 1px; border-style: dotted; border-color: #C0C4C0; margin: 0px; padding: 0px;z-index:10;position: absolute;" +
            "height:" + (this.cTaskNameItem[0].offsetTop - this.parentTask.cTaskNameItem[0].offsetTop) + "px;" +
            "top:" + (this.parentTask.cTaskNameItem[0].offsetTop + 5) + "px;" +
            "left:" + (this.parentTask.cTaskNameItem[0].offsetLeft - 9) + "px;";
    lineVerticalLeft.innerHTML = "&nbsp;";
    this.Chart.panelNames.firstChild.appendChild(lineVerticalLeft);

    var LineHorizontalLeft = document.createElement("div");
    LineHorizontalLeft.noShade = true;
    LineHorizontalLeft.color = "#000000";
    LineHorizontalLeft.style.cssText = "left:" + (this.parentTask.cTaskNameItem[0].offsetLeft - 9) + "px;top:" + (this.cTaskNameItem[0].offsetTop + 5) + "px;z-index:10;" +
            "height:" + 1 + "px;width:" + (this.cTaskNameItem[0].offsetLeft - this.parentTask.cTaskNameItem[0].offsetLeft + 4 ) + "px;position: absolute;border-width: 1px 0px 0px 0px;font-size: 1px;border-style: dotted; border-color: #C0C4C0;margin: 0px; padding: 0px;";
    this.Chart.panelNames.firstChild.appendChild(LineHorizontalLeft);

    arrConnectingLinesNames.push(lineVerticalLeft);
    arrConnectingLinesNames.push(LineHorizontalLeft);*/

    return  arrConnectingLinesNames;

};
/**
 * @desc: creation  connecting lines in panel oData
 * @type: private
 * @topic: 4
 */
GanttTask.prototype.createConnectingLinesDS = function()
{
    var oData = this.Chart.oData.firstChild;
    var arrLines = [];

    var arrowImg = new Image();
    arrowImg.src = this.Chart.imgs + "arr.gif";

    //vertical line
    var lineVerticalRight = document.createElement("div");

    //horizontal line
    var lineHorizontal = document.createElement("div");

    var posXPredecessorTask = parseInt(this.predTask.cTaskItem[0].style.left);
    var posYPredecessorTask = parseInt(this.predTask.cTaskItem[0].style.top);

    var posXChildTask = parseInt(this.cTaskItem[0].style.left);
    var posYChildTask = this.posY + 2;

    //width task item
    var widthChildTask = parseInt(this.predTask.cTaskItem[0].firstChild.firstChild.width);
    var widthPredecessorTask = parseInt(this.predTask.cTaskItem[0].firstChild.firstChild.width);

    if (posYPredecessorTask < posYChildTask)
    {
        lineVerticalRight.style.cssText = "border-width: 0px 0px 0px 1px; border-style: solid; border-color: #4A8F43;margin: 0px; padding: 0px;z-index:0;font-size: 1px;position: absolute;" +
                "height:" + (posYChildTask - this.Chart.heightTaskItem / 2 - posYPredecessorTask - 3) + "px;width:" + 1 + "px;left:" + (posXPredecessorTask + widthPredecessorTask - 20 ) + "px;top:" + (posYPredecessorTask + this.Chart.heightTaskItem) + "px;";

        lineHorizontal.style.cssText = "height:1px;border-color: #4A8F43;border-style: solid;border-width: 1px 0px 0px 0px;margin: 0px; padding: 0px;z-index:0;position: absolute;" +
                "width:" + (15 + (posXChildTask - (widthPredecessorTask + posXPredecessorTask))) + "px;left:" + (posXPredecessorTask + widthPredecessorTask - 20 ) + "px;top:" + (posYChildTask + 2) + "px;";

        arrowImg.style.cssText = "margin: 0px; padding: 0px;width:7px;height:14px;position: absolute;left:" + (posXChildTask - 7) + "px;top:" + (posYChildTask - 1) + "px;";
    } else {
        lineVerticalRight.style.cssText = "border-width: 0px 0px 0px 1px; border-style: solid; border-color: #4A8F43;margin: 0px; padding: 0px;z-index:0;font-size: 1px;position: absolute;" +
                "height:" + (posYPredecessorTask + 2 - posYChildTask) + "px;width:" + 1 + "px;left:" + (posXPredecessorTask + widthPredecessorTask - 20 ) + "px;top:" + (posYChildTask + 2) + "px;";

        lineHorizontal.style.cssText = "height:1px;border-color: #4A8F43;border-style: solid;border-width: 1px 0px 0px 0px;margin: 0px; padding: 0px;z-index:0;position: absolute;" +
                "width:" + (15 + (posXChildTask - (widthPredecessorTask + posXPredecessorTask))) + "px;left:" + (posXPredecessorTask + widthPredecessorTask - 20 ) + "px;top:" + (posYChildTask + 2) + "px;";

        arrowImg.style.cssText = "margin: 0px; padding: 0px;width:7px;height:14px;position: absolute;left:" + (posXChildTask - 7) + "px;top:" + (posYChildTask - 1) + "px;";
    }
    oData.appendChild(lineVerticalRight);
    oData.appendChild(lineHorizontal);
    oData.appendChild(arrowImg);

    arrLines.push(lineVerticalRight);
    arrLines.push(arrowImg);
    arrLines.push(lineHorizontal);

    return arrLines;
};
/**
 * @desc: Shows current tasks
 * @param: task - GanttTask object.
 * @type: private
 * @topic: 3
 */
GanttTask.prototype.showChildTasks = function(task, isOpen)
{
    if (isOpen)
    {
        for (var i = 0; i < task.childTask.length; i++)
        {
            if (task.childTask[i].cTaskItem[0].style.display == "none") {
                task.childTask[i].cTaskItem[0].style.display = "inline";
                task.childTask[i].cTaskNameItem[0].style.display = "inline";
                if (this.Chart.isShowDescTask) {
                    task.childTask[i].showDescTask();
                }

                task.isHide = false;

                if (task.childTask[i].cTaskNameItem[2]) {
                    task.childTask[i].cTaskNameItem[2].style.display = "inline";
                    isOpen = task.childTask[i]._isOpen;
                }

                for (var k = 0; k < task.childTask[i].cTaskItem[1].length; k++) {
                    task.childTask[i].cTaskItem[1][k].style.display = "inline";

                }
                for (var k = 0; k < task.childTask[i].cTaskNameItem[1].length; k++) {
                    task.childTask[i].cTaskNameItem[1][k].style.display = "inline";
                }

                this._heightHideTasks += this.Chart.heightTaskItem + 11;

                if (task.childTask[i].childTask.length > 0) {
                    this.showChildTasks(task.childTask[i], isOpen);
                }

            }
        }
    }
};
/**
 * @desc: hide child task
 * @param: task - (object) GanttTask
 * @type: private
 * @topic: 3
 */
GanttTask.prototype.hideChildTasks = function(task)
{
    for (var i = 0; i < task.childTask.length; i++)
    {
        if (task.childTask[i].cTaskItem[0].style.display != "none")
        {
            task.childTask[i].cTaskItem[0].style.display = "none";
            task.childTask[i].cTaskNameItem[0].style.display = "none";
            if (this.Chart.isShowDescTask) {
                task.childTask[i].hideDescTask();
            }
            task.isHide = true;

            if (task.childTask[i].cTaskNameItem[2]) {
                task.childTask[i].cTaskNameItem[2].style.display = "none";
            }

            for (var k = 0; k < task.childTask[i].cTaskItem[1].length; k++) {
                task.childTask[i].cTaskItem[1][k].style.display = "none";
            }
            for (var k = 0; k < task.childTask[i].cTaskNameItem[1].length; k++) {
                task.childTask[i].cTaskNameItem[1][k].style.display = "none";
            }

            this._heightHideTasks += this.Chart.heightTaskItem + 11;

            if (task.childTask[i].childTask.length > 0) {
                this.hideChildTasks(task.childTask[i]);
            }

        }
    }
};
/**
 * @desc: shift current tasks
 * @param: task - (object) GanttTask
 * @param: height - specifies height on which tasks are shifted
 * @type: private
 * @topic: 4
 */
GanttTask.prototype.shiftCurrentTasks = function(task, height)
{
    this.shiftNextTask(this, height);
    task.Project.shiftNextProject(task.Project, height);
};

GanttProject.prototype.shiftNextProject = function(project, height)
{
    if (project.nextProject) {
        project.nextProject.shiftProject(height);
        this.shiftNextProject(project.nextProject, height);
    }

};
GanttProject.prototype.shiftProject = function(height)
{
    this.projectItem[0].style.top = parseInt(this.projectItem[0].style.top) + height + "px";
    if (this.Chart.isShowDescProject) {
        this.descrProject.style.top = parseInt(this.descrProject.style.top) + height + "px";
    }

    if (this.Chart._showTreePanel) {
        this.projectNameItem.style.top = parseInt(this.projectNameItem.style.top) + height + "px";
    }
    if (this.arrTasks.length > 0)
        this.shiftNextParentTask(this.arrTasks[0], height);

};
GanttProject.prototype.shiftTask = function(task, height)
{
    if (this.Chart._showTreePanel) {

        task.cTaskNameItem[0].style.top = parseInt(task.cTaskNameItem[0].style.top) + height + "px";
        if (task.cTaskNameItem[2]) {
            task.cTaskNameItem[2].style.top = parseInt(task.cTaskNameItem[2].style.top) + height + "px";
        }
        if (task.parentTask && task.cTaskNameItem[1][0])
        {
            task.cTaskNameItem[1][0].style.top = parseInt(task.cTaskNameItem[1][0].style.top) + height + "px";
            task.cTaskNameItem[1][1].style.top = parseInt(task.cTaskNameItem[1][1].style.top) + height + "px";
        }
    }

    task.cTaskItem[0].style.top = parseInt(task.cTaskItem[0].style.top) + height + "px";
    if (this.Chart.isShowDescTask) {
        task.descrTask.style.top = parseInt(task.descrTask.style.top) + height + "px";
    }
    if (task.cTaskItem[1][0])
    {
        task.cTaskItem[1][0].style.top = parseInt(task.cTaskItem[1][0].style.top) + height + "px";
        task.cTaskItem[1][1].style.top = parseInt(task.cTaskItem[1][1].style.top) + height + "px";
        task.cTaskItem[1][2].style.top = parseInt(task.cTaskItem[1][2].style.top) + height + "px";
    }
};
GanttProject.prototype.shiftNextParentTask = function(task, height)
{
    this.shiftTask(task, height);
    this.shiftChildTasks(task, height);

    if (task.nextParentTask) {
        this.shiftNextParentTask(task.nextParentTask, height);
    }

};
GanttProject.prototype.shiftChildTasks = function(task, height)
{
    for (var i = 0; i < task.childTask.length; i++)
    {
        this.shiftTask(task.childTask[i], height);
        if (task.childTask[i].childTask.length > 0) {
            this.shiftChildTasks(task.childTask[i], height);
        }

    }
};

GanttTask.prototype.shiftTask = function(task, height)
{
    if (this.Chart._showTreePanel) {
        task.cTaskNameItem[0].style.top = parseInt(task.cTaskNameItem[0].style.top) + height + "px";
        if (task.cTaskNameItem[2]) {
            task.cTaskNameItem[2].style.top = parseInt(task.cTaskNameItem[2].style.top) + height + "px";
        }
        if (task.parentTask)
        {
            if (task.cTaskNameItem[1].length > 0) if ((parseInt(this.cTaskNameItem[0].style.top) > parseInt(task.parentTask.cTaskNameItem[0].style.top))
                    && (task.cTaskNameItem[1][0].style.display != "none")) {
                task.cTaskNameItem[1][0].style.height = parseInt(task.cTaskNameItem[1][0].style.height) + height + "px";
            } else {
                task.cTaskNameItem[1][0].style.top = parseInt(task.cTaskNameItem[1][0].style.top) + height + "px";
            }
            if (task.cTaskNameItem[1].length > 1) task.cTaskNameItem[1][1].style.top = parseInt(task.cTaskNameItem[1][1].style.top) + height + "px";
        }
    }

    task.cTaskItem[0].style.top = parseInt(task.cTaskItem[0].style.top) + height + "px";
    if (this.Chart.isShowDescTask) {
        task.descrTask.style.top = parseInt(task.descrTask.style.top) + height + "px";
    }
    if (task.predTask)
    {
        if (task.cTaskItem[1].length > 0) if (((parseInt(this.cTaskItem[0].style.top) > parseInt(task.predTask.cTaskItem[0].style.top)) ||
                (this.cTaskItem[0].id == task.predTask.TaskInfo.Id)) &&
                task.cTaskItem[1][0].style.display != "none") {
            task.cTaskItem[1][0].style.height = parseInt(task.cTaskItem[1][0].style.height) + height + "px";
        } else {
            task.cTaskItem[1][0].style.top = parseInt(task.cTaskItem[1][0].style.top) + height + "px";
        }
        if (task.cTaskItem[1].length > 2) {
            task.cTaskItem[1][1].style.top = parseInt(task.cTaskItem[1][1].style.top) + height + "px";
            task.cTaskItem[1][2].style.top = parseInt(task.cTaskItem[1][2].style.top) + height + "px";
        }
    }
};
GanttTask.prototype.shiftNextTask = function(task, height)
{
    if (task.nextChildTask) {
        this.shiftTask(task.nextChildTask, height);
        this.shiftChildTask(task.nextChildTask, height);
        this.shiftNextTask(task.nextChildTask, height);

    } else if (task.parentTask) {
        this.shiftNextTask(task.parentTask, height);

    } else if (task.nextParentTask) {
        this.shiftTask(task.nextParentTask, height);
        this.shiftChildTask(task.nextParentTask, height);
        this.shiftNextTask(task.nextParentTask, height);
    }
};
GanttTask.prototype.shiftChildTask = function(task, height)
{
    for (var i = 0; i < task.childTask.length; i++)
    {
        this.shiftTask(task.childTask[i], height);
        if (task.childTask[i].childTask.length > 0) {
            this.shiftChildTask(task.childTask[i], height);
        }
    }
};

/**
 * @desc: get position of the task on EST
 * @param: est - time of the beginning of the task
 * @type: private
 * @topic: 4
 */
GanttChart.prototype.getPosOnDate = function(est)
{
    return  (est - this.startDate) / (60 * 60 * 1000) * this.hourInPixels;
};
/**
 * @desc: get width on duration
 * @param: duration - duration of current task
 * @type: private
 * @topic: 4
 */
GanttChart.prototype.getWidthOnDuration = function(duration)
{
    return Math.round(this.hourInPixelsWork * duration);
};
/**
 * @desc: end of dragging of task
 * @type: private
 * @topic: 5
 */
GanttTask.prototype.endMove = function()
{
    var width = parseInt(this.cTaskItem[0].style.left) - this.posX;
    var est = this.getDateOnPosition(parseInt(this.cTaskItem[0].style.left));
    est = this.checkPos(est);

    this.wasMoved = this.TaskInfo.EST.valueOf() !=  est.valueOf();

    if (this.checkMove) {
        width = this.Chart.getPosOnDate(est) - this.posX;
        this.moveCurrentTaskItem(width, this.moveChild);
        this.Project.shiftProjectItem();
    }

    this.checkMove = false;
    this.posX = 0;
    this.maxPosXMove = -1;
    this.minPosXMove = -1;
    this.cTaskItem[0].childNodes[1].firstChild.rows[0].cells[0].innerHTML = "";

    if (this.Chart._isFF) document.body.style.cursor = "";
    if (this.Chart._isIE) this.cTaskItem[0].childNodes[2].childNodes[0].style.cursor = "";
};

GanttTask.prototype.checkPos = function(est)
{
    var h = est.getHours();
    if (h >= 12)
    {
        est.setDate(est.getDate() + 1);
        est.setHours(0);

        if ((parseInt(this.cTaskItem[0].firstChild.firstChild.width) + this.Chart.getPosOnDate(est) > this.maxPosXMove) && (this.maxPosXMove != -1))
        {
            est.setDate(est.getDate() - 1);
            est.setHours(0);
        }


    } else if ((h < 12) && (h != 0))
    {
        est.setHours(0);
        if ((this.Chart.getPosOnDate(est) < this.minPosXMove))
        {
            est.setDate(est.getDate() + 1);
        }
    }
    this.cTaskItem[0].style.left = this.Chart.getPosOnDate(est) + "px";

    return  est;

};

/**
 * @desc: returns max position of child task
 * @type: private
 * @topic: 4
 */
GanttTask.prototype.getMaxPosPredChildTaskItem = function()
{
    var posPredChildTaskItem = 0;
    var nextPosPredChildTaskItem = 0;

    for (var i = 0; i < this.childPredTask.length; i++)
    {
        nextPosPredChildTaskItem = this.getMaxPosPredChildTaskItemInTree(this.childPredTask[i]);
        if (nextPosPredChildTaskItem > posPredChildTaskItem)
        {
            posPredChildTaskItem = nextPosPredChildTaskItem;
        }
    }
    return posPredChildTaskItem;

};
/**
 * @desc: returns max position of child task in tree
 * @param: task - (object) task
 * @type: private
 * @topic: 4
 */
GanttTask.prototype.getMaxPosPredChildTaskItemInTree = function(task)
{
    var currentPos = parseInt(task.cTaskItem[0].firstChild.firstChild.width) + parseInt(task.cTaskItem[0].style.left);
    var posPredChildTaskItem = 0;
    var nextPosPredChildTaskItem = 0;

    for (var i = 0; i < task.childPredTask.length; i++)
    {
        nextPosPredChildTaskItem = this.getMaxPosPredChildTaskItemInTree(task.childPredTask[i]);
        if (nextPosPredChildTaskItem > posPredChildTaskItem)
        {
            posPredChildTaskItem = nextPosPredChildTaskItem;
        }
    }

    if (posPredChildTaskItem > currentPos)
    {
        return posPredChildTaskItem;
    }
    else
    {
        return currentPos;
    }

};
/**
 * @desc: get task by id
 * @param: id - Id of GanttTask
 * @type: public
 * @topic: 2
 */
GanttProject.prototype.getTaskById = function(id)
{
    for (var i = 0; i < this.arrTasks.length; i++)
    {
        var task = this.searchTaskInTree(this.arrTasks[i], id);
        if (task) return task;

    }
    return null;
};
/**
 * @desc: search GanttTask in child tasks
 * @param: task  - (object) parent GanttTask
 * @param: id - Id of GanttTask
 * @type: private
 * @topic: 2
 */
GanttProject.prototype.searchTaskInTree = function(task, id)
{
    if (task.TaskInfo.Id == id)
    {
        return task;

    } else
    {
        for (var i = 0; i < task.childTask.length; i++)
        {
            if (task.childTask[i].TaskInfo.Id == id)
            {
                return task.childTask[i];
            }
            else
            {
                if (task.childTask[i].childTask.length > 0)
                {
                    var cTask = this.searchTaskInTree(task.childTask[i], id);
                    if (cTask) return cTask;
                }
            }
        }
    }

    return null;
};
/**
 * @desc: shift current projectItem
 * @type: private
 * @topic: 4
 */
GanttProject.prototype.shiftProjectItem = function()
{
    var posItemL = null;
    var posItemR = null;
    var posProjectItemL = parseInt(this.projectItem[0].style.left);
    var posProjectItemR = parseInt(this.projectItem[0].firstChild.style.width) + parseInt(this.projectItem[0].style.left);
    var widthProjectItem = parseInt(this.projectItem[0].firstChild.style.width);

    for (var t = 0; t < this.arrTasks.length; t++)
    {
        var tmpPosItemL = parseInt(this.arrTasks[t].cTaskItem[0].style.left);
        var tmpPosItemR = parseInt(this.arrTasks[t].cTaskItem[0].style.left) + parseInt(this.arrTasks[t].cTaskItem[0].firstChild.firstChild.width);

        if (!posItemL) {
            posItemL = tmpPosItemL;
        }
        if (!posItemR) {
            posItemR = tmpPosItemR;
        }


        if (posItemL > tmpPosItemL) {
            posItemL = tmpPosItemL;
        }

        if (posItemR < tmpPosItemR) {
            posItemR = tmpPosItemR;
        }

    }

    if (posItemL != posProjectItemL)
    {
        this.Project.StartDate = new Date(this.Chart.startDate);
        this.Project.StartDate.setHours(this.Project.StartDate.getHours() + (posItemL / this.Chart.hourInPixels));
    }

    this.projectItem[0].style.left = posItemL + "px";
    this.resizeProjectItem(posItemR - posItemL);

    this.Duration = Math.round(parseInt(this.projectItem[0].firstChild.width) / (this.Chart.hourInPixelsWork));
    if (this.Chart.isShowDescProject) {
        this.moveDescrProject();
    }
    this.addDayInPanelTime();

};
/**
 * @desc: add one day
 * @type: private
 * @topic: 4
 */
GanttProject.prototype.addDayInPanelTime = function()
{
    var width = parseInt(this.projectItem[0].style.left) + parseInt(this.projectItem[0].firstChild.style.width) + 20;
    if (this.Chart.isShowDescProject) {
        width += this.descrProject.offsetWidth;
    }

    var table = this.Chart.panelTime.firstChild, tbody = table.firstChild;
    if (parseInt(tbody.offsetWidth) < width)
    {
        var countDays = Math.round((width - parseInt(tbody.offsetWidth)) / this.Chart.dayInPixels);
        var row = tbody.rows[1];
        for (var n = 0; n < countDays; n++)
        {
            this.Chart.addPointInTimePanel(row, table);
            this.Chart.addDayInPanelTime(row);
        }
        var w = this.Chart.dayInPixels * (row.cells.length);
        tbody.style.width = w + "px";
        this.Chart.panelTasks.style.width = (w-18) + "px";
    }
};
/**
 * @desc: add event
 * @param: elm - current element
 * @param: evType - string that specifies any of the standard DHTML Events
 * @param: fn -  pointer that specifies the function to call when sEvent fires
 * @type: private
 * @topic: 5
 */
GanttProject.prototype.addEvent = function (elm, evType, fn, useCapture)
{
    if (elm.addEventListener) {
        elm.addEventListener(evType, fn, useCapture);
        return true;
    }
    else if (elm.attachEvent) {
        return elm.attachEvent('on' + evType, fn);
    }
    else {
        elm['on' + evType] = fn;
    }
};
/**
 * @desc: shows popup info
 * @param: event - (object)event
 * @type: private
 * @topic: 4
 */
GanttProject.prototype.getPopUpInfo = function(object, event)
{
    //this.projectItem[0]
    var posX = object.offsetLeft + ((event.layerX == null) ? event.offsetX : event.layerX);
    var posY = object.offsetTop + this.Chart.heightTaskItem + 6;

    var tblInfo = this.Chart.divInfo.lastChild;
    tblInfo.rows[0].cells[0].innerHTML = "<div style='font-family: Arial, Helvetica, Sans-serif; font-size: 12px; font-weight: bold; color: #688060; margin:0 0 4px 0;'>" + this.Project.Name + "</div>";
    tblInfo.rows[0].cells[0].innerHTML += "<span class='st'>Start Date:&nbsp;</span><span class='ut'>" + this.Project.StartDate.getDate() + "." + (this.Project.StartDate.getMonth() + 1) + "." + this.Project.StartDate.getFullYear() + "</span><br/>";
    tblInfo.rows[0].cells[0].innerHTML += "<span class='st'>Duration:&nbsp;</span><span class='ut'>" + this.Duration + " hours</span><br/>";
    tblInfo.rows[0].cells[0].innerHTML += "<span class='st'>Percent Complete:&nbsp;</span><span class='ut'>" + this.percentCompleted + "%</span><br/>";

    this.Chart.divInfo.style.cssText = "z-index:2;position: absolute;display: inline;";

    if (posY + this.Chart.divInfo.lastChild.offsetHeight + 6 > this.Chart.oData.offsetHeight + this.Chart.oData.scrollTop)
    {
        this.Chart.divInfo.style.top = (posY - this.Chart.divInfo.lastChild.offsetHeight - 10 - this.Chart.heightTaskItem) + "px";
    }
    else {
        this.Chart.divInfo.style.top = posY + "px";
    }

    if (this.Chart.divInfo.lastChild.offsetWidth + posX + 10 > this.Chart.oData.offsetWidth + this.Chart.oData.scrollLeft)
    {
        this.Chart.divInfo.style.left = posX - (this.Chart.divInfo.lastChild.offsetWidth + posX + 20 - (this.Chart.oData.offsetWidth + this.Chart.oData.scrollLeft)) + "px";

    } else {
        this.Chart.divInfo.style.left = posX + "px";
    }
};
/**
 * @desc: hides pop up info
 * @type: private
 * @topic: 4
 */
GanttProject.prototype.closePopUpInfo = function()
{
    this.Chart.divInfo.style.display = "none";
};
/**
 * @desc: resize projectItem
 * @param: width - new width
 * @type: private
 * @topic: 4
 */
GanttProject.prototype.resizeProjectItem = function(width)
{
    var percentCompleted = this.percentCompleted;
    if (percentCompleted > 0 && percentCompleted < 100)
    {
        this.projectItem[0].firstChild.style.width = width + "px";
        this.projectItem[0].firstChild.width = width + "px";
        this.projectItem[0].style.width = width + "px";
        this.projectItem[0].firstChild.rows[0].cells[0].firstChild.style.width = Math.round(width * percentCompleted / 100) + "px";
        this.projectItem[0].firstChild.rows[0].cells[1].firstChild.style.width = Math.round(width * (100 - percentCompleted) / 100) + "px";
        this.projectItem[0].lastChild.firstChild.width = width + "px";

    } else if (percentCompleted == 0 || percentCompleted == 100)
    {
        this.projectItem[0].firstChild.style.width = width + "px";
        this.projectItem[0].firstChild.width = width + "px";
        this.projectItem[0].style.width = width + "px";
        this.projectItem[0].firstChild.rows[0].cells[0].firstChild.style.width = width + "px";
        this.projectItem[0].lastChild.firstChild.width = width + "px";
    }
};
/**
 * @desc: Moving of current task
 * @param: width - length of shift of the task
 * @param: moveChild  - true, if move children together
 * @type: private
 * @topic: 4
 */
GanttTask.prototype.moveCurrentTaskItem = function(width, moveChild)
{
    var taskItem = this.cTaskItem[0];
    this.TaskInfo.EST = new Date(this.Chart.startDate);
    this.TaskInfo.EST.setHours(this.TaskInfo.EST.getHours() + (parseInt(taskItem.style.left) / this.Chart.hourInPixels));
    if (this.Chart.isShowDescTask) {
        this.showDescTask();
    }

    if (this.cTaskItem[1].length > 0) {
        this.cTaskItem[1][2].style.width = parseInt(this.cTaskItem[1][2].style.width) + width + "px";
        this.cTaskItem[1][1].style.left = parseInt(this.cTaskItem[1][1].style.left) + width + "px";
    }

    for (var i = 0; i < this.childTask.length; i++) {
        if (!this.childTask[i].predTask) {
            this.moveChildTaskItems(this.childTask[i], width, moveChild);
        }
    }

    for (var i = 0; i < this.childPredTask.length; i++) {
        this.moveChildTaskItems(this.childPredTask[i], width, moveChild);
    }

};
/**
 * @desc: Moving of child tasks
 * @param: task - (object) GanttTask
 * @param: width - length of shift of the task
 * @param: moveChild  - true, if move children together
 * @type: private
 * @topic: 4
 */
GanttTask.prototype.moveChildTaskItems = function(task, width, moveChild)
{
    var taskItem = task.cTaskItem[0];

    if (moveChild)
    {
        taskItem.style.left = parseInt(taskItem.style.left) + width + "px";
        task.addDayInPanelTime();
        task.TaskInfo.EST = new Date(this.Chart.startDate);
        task.TaskInfo.EST.setHours(task.TaskInfo.EST.getHours() + (parseInt(taskItem.style.left) / this.Chart.hourInPixels));

        for (var n = 0; n < task.cTaskItem[1].length; n++) {
            task.cTaskItem[1][n].style.left = parseInt(task.cTaskItem[1][n].style.left) + width + "px";
        }

        for (var i = 0; i < task.childTask.length; i++) {
            if (!task.childTask[i].predTask) {
                this.moveChildTaskItems(task.childTask[i], width, moveChild);
            }
        }

        for (var i = 0; i < task.childPredTask.length; i++) {
            this.moveChildTaskItems(task.childPredTask[i], width, moveChild);
        }
    }
    else
    {
        if (task.cTaskItem[1].length > 0)
        {
            task.cTaskItem[1][2].style.left = parseInt(task.cTaskItem[1][2].style.left) + width + "px";
            task.cTaskItem[1][2].style.width = parseInt(task.cTaskItem[1][2].style.width) - width + "px";
            task.cTaskItem[1][0].style.left = parseInt(task.cTaskItem[1][0].style.left) + width + "px";
        }
    }
    if (this.Chart.isShowDescTask) {
        task.moveDescTask();
    }
};
/**
 * @desc: Addition of new day in panel of time
 * @type: private
 * @topic: 4
 */
GanttTask.prototype.addDayInPanelTime = function()
{
    var taskItem = this.cTaskItem[0];
    var width = parseInt(taskItem.style.left) + parseInt(taskItem.firstChild.firstChild.width) + 20;
    if (this.Chart.isShowDescTask) {
        width += this.descrTask.offsetWidth;
    }

    var table = this.Chart.panelTime.firstChild, tbody = table.firstChild;
    if (parseInt(tbody.offsetWidth) < width)
    {
        var row = tbody.rows[1];
        var countDays = Math.round((width + 20 - parseInt(tbody.offsetWidth)) / this.Chart.dayInPixels);
        for (var n = 0; n < countDays; n++)
        {
            this.Chart.addPointInTimePanel(row, table);
            this.Chart.addDayInPanelTime(row);
        }
        var w = this.Chart.dayInPixels * (row.cells.length);
        tbody.style.width = w + "px";
        this.Chart.panelTasks.style.width = (w-18) + "px";
    }
};
/**
 * @desc: return of date on position of task
 * @param: position - current position of task
 * @type: private
 * @topic: 4
 */
GanttTask.prototype.getDateOnPosition = function(position)
{
    var date = new Date(this.Chart.startDate);
    date.setHours(date.getHours() + (position / this.Chart.hourInPixels));
    return date;
};
/**
 * @desc: moving of current task
 * @param: event - (object) event
 * @type: private
 * @topic: 4
 */
GanttTask.prototype.moveItem = function(event)
{
    var pageX = event.screenX;
    var posTaskItem = (this.posX + (pageX - this.MouseX));
    var widthTaskItem = parseInt(this.cTaskItem[0].childNodes[0].firstChild.width);
    var posTaskItemR = posTaskItem + widthTaskItem;

    if (this.checkMove)
    {
        var date = this.getDateOnPosition(posTaskItem);
        var res = this.Chart.callEvent("onTaskDragging", [this,date])!==false;
        if (res && ((this.minPosXMove <= posTaskItem))
                && ((posTaskItemR <= this.maxPosXMove) || (this.maxPosXMove == -1)))
        {
            this.moveTaskItem(posTaskItem);
        }
    }
};
/**
 * @desc: shift taskItem
 * @param: posX - position of task
 * @type: private
 * @topic: 4
 */
GanttTask.prototype.moveTaskItem = function(posX)
{
    this.addDayInPanelTime();
    this.cTaskItem[0].style.left = posX + "px";
    var date = this.getDateOnPosition(posX); 
    this.cTaskItem[0].childNodes[1].firstChild.rows[0].cells[0].innerHTML = date.getDate() + '.' + (date.getMonth() + 1) + '.' + date.getUTCFullYear();
};
/**
 * @desc: resize current task
 * @param: event  - (object) event
 * @type: private
 * @topic: 4
 */
GanttTask.prototype.resizeItem = function(event)
{
    if (this.checkResize)
    {
        var MouseX = event.screenX;
        var widthTaskItem = this.taskItemWidth + (MouseX - this.MouseX);

        var countHours = Math.round(widthTaskItem / this.Chart.hourInPixelsWork);
        if (this.Chart.callEvent("onTaskResizing", [this,countHours])===false) return;

        if (widthTaskItem >= this.taskItemWidth)
        {
            if ((widthTaskItem <= this.maxWidthResize) || (this.maxWidthResize == -1))
            {
                this.resizeTaskItem(widthTaskItem);
                this.addDayInPanelTime();

            } else if ((this.maxWidthResize != -1) && (widthTaskItem > this.maxWidthResize))
            {
                this.resizeTaskItem(this.maxWidthResize);
            }
        } else if (widthTaskItem <= this.taskItemWidth)
        {
            if (widthTaskItem >= this.minWidthResize)
            {
                this.resizeTaskItem(widthTaskItem);
            }
            else if (widthTaskItem < this.minWidthResize)
            {
                this.resizeTaskItem(this.minWidthResize);
            }
        }
    }
};
/**
 * @desc: resize current taskItem
 * @param: width -  width of current taskItem
 * @type: private
 * @topic: 4
 */
GanttTask.prototype.resizeTaskItem = function(width)
{
    var taskItem = this.cTaskItem[0];
    var countHours = Math.round(width / this.Chart.hourInPixelsWork);
    var c = taskItem.childNodes[0].firstChild.rows[0].cells[0];
    if (c)
    {
        c.firstChild.style.width = parseInt(c.width) * width / 100 + "px";
    }
    c = taskItem.childNodes[0].firstChild.rows[0].cells[1];
    if (c)
    {
        c.firstChild.style.width = parseInt(c.width) * width / 100 + "px";
    }

    taskItem.childNodes[0].firstChild.width = width + "px";
    taskItem.childNodes[1].firstChild.width = width + "px";

    //resize info
    this.cTaskItem[0].childNodes[1].firstChild.rows[0].cells[0].innerHTML = countHours;
    taskItem.childNodes[2].childNodes[0].style.width = width + "px";
    taskItem.childNodes[2].childNodes[1].style.left = width - 10 + "px";
};
/**
 * @desc: end of stretch of task
 * @param: event  - (object) event
 * @type: private
 * @topic: 4
 */
GanttTask.prototype.endResizeItem = function()
{
    var taskItem = this.cTaskItem[0];
    this.wasResized = this.taskItemWidth != parseInt(taskItem.childNodes[0].firstChild.width);
    if (this.wasResized)
    {
        var posXL = taskItem.offsetLeft;
        var posXR = taskItem.offsetLeft + parseInt(taskItem.childNodes[0].firstChild.width);
        this.TaskInfo.Duration = Math.round((posXR - posXL) / this.Chart.hourInPixelsWork);
        if (this.childPredTask.length > 0)
        {
            for (var j = 0; j < this.childPredTask.length; j++)
            {
                this.childPredTask[j].cTaskItem[1][2].style.width = parseInt(this.childPredTask[j].cTaskItem[1][2].style.width) - (parseInt(taskItem.childNodes[0].firstChild.width) - this.taskItemWidth) + "px";
                this.childPredTask[j].cTaskItem[1][2].style.left = parseInt(this.childPredTask[j].cTaskItem[1][2].style.left) + (parseInt(taskItem.childNodes[0].firstChild.width) - this.taskItemWidth) + "px";
                this.childPredTask[j].cTaskItem[1][0].style.left = parseInt(this.childPredTask[j].cTaskItem[1][0].style.left) + (parseInt(taskItem.childNodes[0].firstChild.width) - this.taskItemWidth) + "px";
            }
        }
    }
    this.cTaskItem[0].childNodes[1].firstChild.rows[0].cells[0].innerHTML = "";
    this.checkResize = false;
    this.taskItemWidth = 0;
    this.MouseX = 0;
    if (this.Chart.isShowDescTask) {
        this.showDescTask();
    }
    this.Project.shiftProjectItem();

    if (this.Chart._isFF) document.body.style.cursor = "";
};

GanttProject.prototype.moveDescrProject = function()
{
    this.descrProject.style.left = (parseInt(this.projectItem[0].style.left) + this.Duration * this.Chart.hourInPixelsWork + 10);
    this.descrProject.innerHTML = this.getDescStr();
};

GanttProject.prototype.showDescrProject = function()
{
    var posX = (parseInt(this.projectItem[0].style.left) + this.Duration * this.Chart.hourInPixelsWork + 10);
    this.descrProject.style.left = posX + "px";
    this.descrProject.style.visibility = 'visible';
    this.descrProject.innerHTML = this.getDescStr();
};

GanttProject.prototype.hideDescrProject = function()
{
    this.descrProject.style.visibility = 'hidden';
};

GanttProject.prototype.getDescStr = function()
{
    var str = '', delim = ", ";

    for (var i = 0; i < this.Chart.paramShowProject.length; i++) {

        switch (this.Chart.paramShowProject[i]) {
            case "Name":
                if (str != "")str += delim;
                str += this.Project[this.Chart.paramShowProject[i]];
                break;
            case "StartDate":
                if (str != "")str += delim;
                var d = this.Project[this.Chart.paramShowProject[i]];
                str += d.getDate() + "." + (d.getMonth() + 1) + "." + d.getFullYear();
                break;
            case "Duration":
                if (str != "")str += delim;
                str += this[this.Chart.paramShowProject[i]] + "h";
                break;
            case "percentCompleted":
                if (str != "")str += delim;
                str += this[this.Chart.paramShowProject[i]] + "%";
                break;

            default:
                break;
        }

    }
    return str;
};


GanttProject.prototype.createDescrProject = function()
{
    var posX = (this.posX + this.Duration * this.Chart.hourInPixelsWork + 10);
    var divDesc = document.createElement("div");
    divDesc.style.cssText += ";z-index:1;position:absolute;left:" + posX + "px;top:" + this.posY + "px;";
    divDesc.innerHTML = this.getDescStr();
    divDesc.className = "descProject";
    this.descrProject = divDesc;

    if (this.Project.ParentTasks.length == 0) {
        this.descrProject.style.visibility = 'hidden';
    }

    if (this.Chart._showTooltip)
    {
        var self = this;
        var getPopUpInfo = function(e) {
            if ((!self.Chart._isMove) && (!self.Chart._isResize))  self.getPopUpInfo(self.descrProject, e);
        };
        var closePopUpInfo = function() {
            self.closePopUpInfo();
        };

        this.addEvent(divDesc, 'mouseover', getPopUpInfo, false);
        this.addEvent(divDesc, 'mouseout', closePopUpInfo, false);
    }
    return  divDesc;
};

/**
 * @desc: creation of projectItem
 * @type: private
 * @topic: 0
 */
GanttProject.prototype.createProjectItem = function()
{
    var self = this;
    this.percentCompleted = this.getPercentCompleted();
    this.Duration = this.getDuration();

    var projectItem = document.createElement("div");
    projectItem.id = this.Project.Id;
    projectItem.style.cssText = ";z-index:1;position: absolute;left:" + this.posX + "px;top:" + this.posY + "px;";
    projectItem.style.width = this.Duration * this.Chart.hourInPixelsWork + "px";

    var tblProjectItem = document.createElement("table");
    projectItem.appendChild(tblProjectItem);
    tblProjectItem.cellPadding = "0";
    tblProjectItem.cellSpacing = "0";
    tblProjectItem.style.cssText = "border: solid 1px #BC810D;";
    var width = this.Duration * this.Chart.hourInPixelsWork;
    tblProjectItem.width = ((width == 0) ? 1 : width) + "px";
    tblProjectItem.style.width = ((width == 0) ? 1 : width) + "px";

    var rowprojectItem = tblProjectItem.insertRow(tblProjectItem.rows.length);

    if (this.percentCompleted != -1)
    {
        if (this.percentCompleted != 0)
        {
            var cellprojectItem = document.createElement("TD");
            rowprojectItem.appendChild(cellprojectItem);
            cellprojectItem.width = this.percentCompleted + "%";
            cellprojectItem.style.lineHeight = "1px";
            var imgPr = document.createElement("img");
            imgPr.style.width = (this.percentCompleted * this.Duration * this.Chart.hourInPixelsWork) / 100 + "px";
            imgPr.style.height = this.Chart.heightTaskItem + "px";
            cellprojectItem.appendChild(imgPr);
            imgPr.src = this.Chart.imgs + "parentnode_filled.png";

        }

        if (this.percentCompleted != 100)
        {
            var cellprojectItem = document.createElement("TD");
            rowprojectItem.appendChild(cellprojectItem);
            cellprojectItem.width = (100 - this.percentCompleted) + "%";
            cellprojectItem.style.lineHeight = "1px";
            var imgPr = document.createElement("img");
            imgPr.style.width = ((100 - this.percentCompleted) * this.Duration * this.Chart.hourInPixelsWork) / 100 + "px";
            imgPr.style.height = this.Chart.heightTaskItem + "px";
            cellprojectItem.appendChild(imgPr);
            imgPr.src = this.Chart.imgs + "progress_bg.png";
        }

    } else
    {
        var cellprojectItem = document.createElement("TD");
        rowprojectItem.appendChild(cellprojectItem);
        cellprojectItem.width = "1px";
        cellprojectItem.style.lineHeight = "1px";
        var imgPr = document.createElement("img");
        imgPr.style.width = "1px";
        imgPr.style.height = this.Chart.heightTaskItem;
        cellprojectItem.appendChild(imgPr);
        imgPr.src = this.Chart.imgs + "progress_bg.png";

    }

    var divTaskInfo = document.createElement("div");
    divTaskInfo.style.cssText = "text-align:center;z-index:2;position:absolute;left:0px;top:0px;";
    //

    var tblTaskInfo = document.createElement("table");
    divTaskInfo.appendChild(tblTaskInfo);
    tblTaskInfo.cellPadding = "0";
    tblTaskInfo.cellSpacing = "0";
    tblTaskInfo.height = this.Chart.heightTaskItem + "px";
    tblTaskInfo.width = ((this.Duration * this.Chart.hourInPixelsWork == 0) ? 1 : this.Duration * this.Chart.hourInPixelsWork) + "px";

    var rowTaskInfo = tblTaskInfo.insertRow(0);
    var cellTaskInfo = document.createElement("td");
    cellTaskInfo.align = "center";
    cellTaskInfo.vAlign = "top";
    cellTaskInfo.height = this.Chart.heightTaskItem + "px";
    cellTaskInfo.className = "moveInfo";
    cellTaskInfo.style.cssText = ";white-space:nowrap;";
    rowTaskInfo.appendChild(cellTaskInfo);
    projectItem.appendChild(divTaskInfo);

    if (this.Project.ParentTasks.length == 0)
    {
        projectItem.style.display = "none";

    }

    if (this.Chart._showTooltip)
    {
        var getPopUpInfo = function(e) {
            if ((!self.Chart._isMove) && (!self.Chart._isResize))  self.getPopUpInfo(self.projectItem[0], e);
        };
        var closePopUpInfo = function() {
            self.closePopUpInfo();
        };

        this.addEvent(divTaskInfo, 'mouseover', getPopUpInfo, false);
        this.addEvent(divTaskInfo, 'mouseout', closePopUpInfo, false);
    }
    return projectItem;
};
/**
 * @desc: Creation of projectNameItem
 * @type: private
 * @topic: 0
 */
GanttProject.prototype.createProjectNameItem = function()
{
    var self = this;
    var divName = document.createElement("div");
    divName.style.cssText = "cursor:pointer;color:#003366;font-weight:bold;font-size:12px;font-family:Tahoma,Arial;white-space:nowrap;height:15px;z-index:1;position:absolute;left:" + 5 + "px;top:" + this.posY + "px;";
    divName.innerHTML = this.Project.Name;
    divName.title = this.Project.Name;
    if (this.Chart.isShowConMenu)
    {
        var showContMenu = function(event) {

            if (self.Chart.contextMenu.clear) self.Chart.contextMenu.clear();

            var hideContMenu = null;
            if (!self.Chart._isIE)
            {
                hideContMenu = function() {
                    self.Chart.contextMenu.hideContextMenu();
                    self.Chart.content.removeEventListener("mousedown", hideContMenu, false);
                };

            } else
            {
                hideContMenu = function() {
                    self.Chart.contextMenu.hideContextMenu();
                    self.Chart.content.detachEvent("mousedown", hideContMenu);
                };
            }

            self.Chart.content.onmousedown = hideContMenu;

            if (!self.Chart._isIE)
            {
                event.stopPropagation();

            } else
            {
                event.cancelBubble = true;
            }

            self.Chart._showContextMenu(event, self);

        };

        if (this.Chart._isIE)
        {
            this.addEvent(divName, "contextmenu", function(e) {
                showContMenu(e);
                return false;
            }, false);

        } else
        {
            this.addEvent(divName, "contextmenu", function(e) {
                e.preventDefault();
                showContMenu(e);
            }, false);
        }

    }
    return divName;
};
/**
 * @desc: calculates and returns percent completed of project
 * @type: public
 * @topic: 0
 */
GanttProject.prototype.getPercentCompleted = function()
{
    var sum = 0;
    var percentCompleted = 0;

    for (var i = 0; i < this.Project.ParentTasks.length; i++) {
        sum += parseInt(this.Project.ParentTasks[i].PercentCompleted);
    }
    if (this.Project.ParentTasks.length != 0) {
        return  percentCompleted = Math.round(sum / this.Project.ParentTasks.length);
    }
    else {
        return  percentCompleted = -1;
    }
};
/**
 * @desc: calculates and returns the duration of project in hours
 * @type: public
 * @topic: 0
 */
GanttProject.prototype.getDuration = function()
{
    var duration = 0;
    var tmpDuration = 0;
    if (this.Project.ParentTasks.length > 0)
    {
        for (var i = 0; i < this.Project.ParentTasks.length; i++)
        {
            tmpDuration = this.Project.ParentTasks[i].Duration * 24 / this.Chart.hoursInDay + (this.Project.ParentTasks[i].EST - this.Chart.startDate) / (60 * 60 * 1000);
            if (tmpDuration > duration)
            {
                duration = tmpDuration;
            }
        }
        return ((duration - this.posX) / 24) * this.Chart.hoursInDay;

    } else
    {
        return 0;
    }

};
/**
 * @desc: returns id of project.
 * @type: public
 * @topic: 0
 */
GanttProject.prototype.getId = function()
{
    return this.Project.Id;
};
/**
 * @desc: returns name of project.
 * @type: public
 * @topic: 0
 */
GanttProject.prototype.getName = function()
{
    return this.Project.Name;
};
/**
 * @desc: returns start date of project.
 * @type: public
 * @topic: 0
 */
GanttProject.prototype.getStartDate = function()
{
    return this.Project.StartDate;
};

/**
 * @desc: add event
 * @param: elm - current element
 * @param: evType - string that specifies any of the standard DHTML Events
 * @param: fn -  pointer that specifies the function to call when sEvent fires
 * @type:  private
 * @topic: 5
 */
GanttTask.prototype.addEvent = function (elm, evType, fn, useCapture)
{
    if (elm.addEventListener) {
        elm.addEventListener(evType, fn, useCapture);
        return true;
    }
    else if (elm.attachEvent) {
        return elm.attachEvent('on' + evType, fn);
    }
    else {
        elm['on' + evType] = fn;
    }
};
/**
 * @desc: the beginning of movement of task
 * @param: event  - (object)event
 * @type:  private
 * @topic: 5
 */
GanttTask.prototype.startMove = function (event)
{
    this.moveChild = event.ctrlKey;
    this.MouseX = event.screenX;

    this.getMoveInfo();

    this.checkMove = true;

    if (this.Chart.isShowDescTask) {
        this.hideDescTask();
    }
    if (this.Chart._isFF) document.body.style.cursor = "move";
    if (this.Chart._isIE) event.srcElement.style.cursor = "move";
};

GanttTask.prototype.showDescTask = function()
{
    var posX = (parseInt(this.cTaskItem[0].style.left) + this.TaskInfo.Duration * this.Chart.hourInPixelsWork + 10);
    this.descrTask.style.left = posX + "px";
    this.descrTask.innerHTML = this.getDescStr();
    this.descrTask.style.visibility = 'visible';

};
GanttTask.prototype.hideDescTask = function()
{
    this.descrTask.style.visibility = 'hidden';
};
GanttTask.prototype.getDescStr = function()
{
    var str = '', delim = ", ";
    for (var i = 0; i < this.Chart.paramShowTask.length; i++) {
        var prop = this.Chart.paramShowTask[i], propValue = this.TaskInfo[prop];
        switch (prop) {
            case "Name":
                if (str != "")str += delim;
                str += propValue;
                break;
            case "EST":
                if (str != "")str += delim;
                str += propValue.getDate() + "." + (propValue.getMonth() + 1) + "." + propValue.getFullYear();
                break;
            case "S-F":
                if (str != "")str += delim;
                propValue = this.TaskInfo["EST"];
                str += propValue.getDate() + "." + (propValue.getMonth() + 1) + "." + propValue.getFullYear() + " - ";
                propValue = this.getFinishDate();
                str += propValue.getDate() + "." + (propValue.getMonth() + 1) + "." + propValue.getFullYear();
                break;
            case "Duration":
                if (str != "")str += delim;
                str += propValue + "h";
                break;
            case "PercentCompleted":
                if (str != "")str += delim;
                str += propValue + "%";
                break;
            default:
                break;
        }
    }
    return str;
};
/**
 * @desc: returns id of task
 * @type: public
 * @topic: 0
 */
GanttTask.prototype.getId = function()
{
    return this.TaskInfo.Id;
};
/**
 * @desc: returns name of task
 * @type: public
 * @topic: 0
 */
GanttTask.prototype.getName = function()
{
    return this.TaskInfo.Name;
};
/**
 * @desc: returns duration of task (in hours)
 * @type: public
 * @topic: 0
 */
GanttTask.prototype.getDuration = function()
{
    return this.TaskInfo.Duration;
};
/**
 * @desc: returns EST of task
 * @type: public
 * @topic: 0
 */
GanttTask.prototype.getEST = function()
{
    return this.TaskInfo.EST;
};
/**
 * @desc: calculates and returns FinishDate of task
 * @type: public
 * @topic: 0
 */
GanttTask.prototype.getFinishDate = function()
{
    var date = new Date(this.TaskInfo.EST);
    date.setDate(date.getDate() + parseInt((this.TaskInfo["Duration"]-1)/this.Chart.hoursInDay+1)-1);
    return date;
};
/**
 * @desc: returns PercentCompleted of task
 * @type: public
 * @topic: 0
 */
GanttTask.prototype.getPercentCompleted = function()
{
    return this.TaskInfo.PercentCompleted;
};
/**
 * @desc: returns PredecessorTaskId of task
 * @type: public
 * @topic: 0
 */
GanttTask.prototype.getPredecessorTaskId = function()
{
    return this.TaskInfo.PredecessorTaskId ? this.TaskInfo.PredecessorTaskId : null;
};
/**
 * @desc: returns ParentTaskId of task
 * @type: public
 * @topic: 0
 */
GanttTask.prototype.getParentTaskId = function()
{
    return this.parentTask ? this.parentTask.getId() : null;
};

GanttTask.prototype.moveDescTask = function()
{
    var posX = (parseInt(this.cTaskItem[0].style.left) + this.TaskInfo.Duration * this.Chart.hourInPixelsWork + 10);
    this.descrTask.style.left = posX + "px";
};

/**
 * @desc:  Defines max and min position of movement
 * @type:  private
 * @topic: 4
 */
GanttTask.prototype.getMoveInfo = function()
{
    this.posX = parseInt(this.cTaskItem[0].style.left);
    var widthTaskItem = parseInt(this.cTaskItem[0].childNodes[0].firstChild.width);
    var posParentTaskItem = (this.parentTask == null) ? 0 : parseInt(this.parentTask.cTaskItem[0].style.left);
    var posPredTaskItem = (this.predTask == null) ? 0 : parseInt(this.predTask.cTaskItem[0].style.left) + parseInt(this.predTask.cTaskItem[0].childNodes[0].firstChild.width);
    var widthParentTaskItem = (this.parentTask == null) ? 0 : parseInt(this.parentTask.cTaskItem[0].childNodes[0].firstChild.width);

    var childPredPosX = 0;
    var childParentPosX = 0;
    var childParentPosXR = 0;
    if (this.childPredTask.length > 0)
    {
        var posChildTaskItem = null;
        for (var n = 0; n < this.childPredTask.length; n++)
        {
            if ((!posChildTaskItem) || ((posChildTaskItem) && (posChildTaskItem > parseInt(this.childPredTask[n].cTaskItem[0].style.left))))
            {
                posChildTaskItem = parseInt(this.childPredTask[n].cTaskItem[0].style.left);
            }
        }
        childPredPosX = posChildTaskItem;
    }
    if (this.childTask.length > 0)
    {
        var posChildTaskItemR = null;
        for (var n = 0; n < this.childTask.length; n++)
        {
            if ((!posChildTaskItemR) || ((posChildTaskItemR) && (posChildTaskItemR > (parseInt(this.childTask[n].cTaskItem[0].style.left)))))
            {
                posChildTaskItemR = parseInt(this.childTask[n].cTaskItem[0].style.left);
            }
        }
        childParentPosXR = posChildTaskItemR;

        var posChildTaskItem = null;
        for (var n = 0; n < this.childTask.length; n++)
        {
            if ((!posChildTaskItem) || ((posChildTaskItem) && (posChildTaskItem < (parseInt(this.childTask[n].cTaskItem[0].style.left) + parseInt(this.childTask[n].cTaskItem[0].firstChild.firstChild.width)))))
            {
                posChildTaskItem = parseInt(this.childTask[n].cTaskItem[0].style.left) + parseInt(this.childTask[n].cTaskItem[0].firstChild.firstChild.width);
            }
        }

        childParentPosX = posChildTaskItem;
    }

    if (!this.moveChild)
    {
        if (this.childPredTask.length > 0) {
            if (this.maxPosXMove < childPredPosX) this.maxPosXMove = childPredPosX;
        }
        if (this.childTask.length > 0) {
            if ((this.childPredTask.length > 0) && (this.maxPosXMove - widthTaskItem) > childParentPosXR) this.maxPosXMove = this.maxPosXMove - ((this.maxPosXMove - widthTaskItem) - childParentPosXR);
            if (!(this.childPredTask.length > 0)) this.maxPosXMove = childParentPosXR + widthTaskItem;
            this.minPosXMove = (childParentPosX - widthTaskItem);
        }

        if (posParentTaskItem > 0)
        {
            if ((!(this.childPredTask.length > 0)) && (this.childTask.length > 0)) {
                if (this.maxPosXMove > posParentTaskItem + widthParentTaskItem) {
                    this.maxPosXMove = posParentTaskItem + widthParentTaskItem;
                }
            }
            if (this.minPosXMove <= posParentTaskItem) {
                this.minPosXMove = posParentTaskItem;
            }
            if ((!(this.childTask.length > 0)) && (!(this.childPredTask.length > 0))) {
                this.maxPosXMove = posParentTaskItem + widthParentTaskItem;

            } else if ((!(this.childTask.length > 0)) && (this.childPredTask.length > 0)) {
                if ((posParentTaskItem + widthParentTaskItem) > posPredTaskItem) {
                    this.maxPosXMove = childPredPosX;
                }
            }
        }

        if (posPredTaskItem > 0) {
            if (this.minPosXMove <= posPredTaskItem) {
                this.minPosXMove = posPredTaskItem;
            }
        }
        if ((posPredTaskItem == 0) && (posParentTaskItem == 0)) {
            if (this.minPosXMove <= this.Chart.initialPos) {
                this.minPosXMove = this.Chart.initialPos;
            }
        }
    } else
    {
        if ((posParentTaskItem > 0) && (posPredTaskItem == 0))
        {
            this.minPosXMove = posParentTaskItem;
            this.maxPosXMove = posParentTaskItem + widthParentTaskItem;

        } else if ((posParentTaskItem == 0) && (posPredTaskItem == 0))
        {
            this.minPosXMove = this.Chart.initialPos;
            this.maxPosXMove = -1;

        } else if ((posParentTaskItem > 0) && (posPredTaskItem > 0))
        {
            this.minPosXMove = posPredTaskItem;
            this.maxPosXMove = posParentTaskItem + widthParentTaskItem;

        } else if ((posParentTaskItem == 0) && (posPredTaskItem > 0))
        {
            this.minPosXMove = posPredTaskItem;
            this.maxPosXMove = -1;
        }

        if ((this.parentTask) && (this.childPredTask.length > 0))
        {
            var posChildTaskItem = this.getMaxPosPredChildTaskItem(this);
            var posParentTaskItem = parseInt(this.parentTask.cTaskItem[0].style.left) + parseInt(this.parentTask.cTaskItem[0].firstChild.firstChild.width);
            this.maxPosXMove = this.posX + widthTaskItem + posParentTaskItem - posChildTaskItem;
        }
    }
};
/**
 * @desc: The beginning of extension of task
 * @param: event - (object) event
 * @type:  private
 * @topic: 5
 */
GanttTask.prototype.startResize = function(event)
{
    this.MouseX = event.screenX;
    this.getResizeInfo();
    if (this.Chart.isShowDescTask) {
        this.hideDescTask();
    }
    this.checkResize = true;
    this.taskItemWidth = parseInt(this.cTaskItem[0].firstChild.firstChild.width);
    if (this.Chart._isFF)document.body.style.cursor = "e-resize";

};
/**
 * @desc:  Defines max and min position of stretchings
 * @type:  private
 * @topic: 4
 */
GanttTask.prototype.getResizeInfo = function()
{
    var taskItem = this.cTaskItem[0];
    var posParentTaskItem = (this.parentTask == null) ? 0 : parseInt(this.parentTask.cTaskItem[0].style.left);
    var widthParentTaskItem = (this.parentTask == null) ? 0 : parseInt(this.parentTask.cTaskItem[0].childNodes[0].firstChild.width);
    var posTaskItem = parseInt(this.cTaskItem[0].style.left);

    var childPredPosX = 0;
    var childParentPosX = 0;
    if (this.childPredTask.length > 0)
    {
        var posChildTaskItem = null;
        for (var n = 0; n < this.childPredTask.length; n++)
        {
            if ((!posChildTaskItem) || ((posChildTaskItem) && (posChildTaskItem > parseInt(this.childPredTask[n].cTaskItem[0].style.left))))
            {
                posChildTaskItem = parseInt(this.childPredTask[n].cTaskItem[0].style.left);

            }
        }
        childPredPosX = posChildTaskItem;
    }

    if (this.childTask.length > 0)
    {
        var posChildTaskItem = null;
        for (var n = 0; n < this.childTask.length; n++)
        {
            if ((!posChildTaskItem) || ((posChildTaskItem) && (posChildTaskItem < (parseInt(this.childTask[n].cTaskItem[0].style.left) + parseInt(this.childTask[n].cTaskItem[0].firstChild.firstChild.width)))))
            {
                posChildTaskItem = parseInt(this.childTask[n].cTaskItem[0].style.left) + parseInt(this.childTask[n].cTaskItem[0].firstChild.firstChild.width);
            }
        }

        childParentPosX = posChildTaskItem;
    }

    this.minWidthResize = this.Chart.dayInPixels;

    if (this.childTask.length > 0)
    {
        this.minWidthResize = childParentPosX - posTaskItem;
    }

    if ((this.childPredTask.length > 0) && (!this.parentTask))
    {
        this.maxWidthResize = childPredPosX - posTaskItem;

    } else if ((this.childPredTask.length > 0) && (this.parentTask))
    {
        var w1 = posParentTaskItem + widthParentTaskItem - posTaskItem;
        var w2 = childPredPosX - posTaskItem;
        this.maxWidthResize = Math.min(w1, w2);

    } else if ((this.childPredTask.length == 0) && (this.parentTask))
    {
        this.maxWidthResize = posParentTaskItem + widthParentTaskItem - posTaskItem;
    }

};
/**
 * @desc: creation of taskItem
 * @type: private
 * @topic: 0
 */
GanttTask.prototype.createTaskItem = function()
{
    var self = this;
    this.posX = this.Chart.getPosOnDate(this.TaskInfo.EST);

    var itemControl = document.createElement("div");
    itemControl.id = this.TaskInfo.Id;
    itemControl.style.cssText = ";z-index:1;position:absolute;left:" + this.posX + "px;top:" + this.posY + "px;";

    var divTaskItem = document.createElement("div");
    itemControl.appendChild(divTaskItem);
    divTaskItem.style.cssText = "z-index:1;position: absolute;left:0px;top:0px;";

    var tblTaskItem = document.createElement("table");
    divTaskItem.appendChild(tblTaskItem);
    tblTaskItem.cellPadding = "0";
    tblTaskItem.cellSpacing = "0";
    tblTaskItem.width = this.TaskInfo.Duration * this.Chart.hourInPixelsWork + "px";
    tblTaskItem.style.cssText = "border: solid 1px #6589A9;";

    var rowTblTask = tblTaskItem.insertRow(tblTaskItem.rows.length);

    if (this.TaskInfo.PercentCompleted != 0)
    {
        var cellTblTask = document.createElement("td");
        rowTblTask.appendChild(cellTblTask);
        cellTblTask.height = this.Chart.heightTaskItem + "px";
        cellTblTask.width = this.TaskInfo.PercentCompleted + "%";
        cellTblTask.style.lineHeight = "1px";
        var imgPr = document.createElement("img");
        imgPr.style.width = (this.TaskInfo.PercentCompleted * this.TaskInfo.Duration * this.Chart.hourInPixelsWork) / 100 + "px";
        imgPr.style.height = this.Chart.heightTaskItem + "px";
        cellTblTask.appendChild(imgPr);
        imgPr.src = this.Chart.imgs + "progress_filled.png";
    }

    if (this.TaskInfo.PercentCompleted != 100)
    {
        var cellTblTask = document.createElement("td");
        rowTblTask.appendChild(cellTblTask);
        cellTblTask.height = this.Chart.heightTaskItem + "px";
        cellTblTask.width = (100 - this.TaskInfo.PercentCompleted) + "%";
        cellTblTask.style.lineHeight = "1px";
        var imgPrF = document.createElement("img");
        imgPrF.style.width = ((100 - this.TaskInfo.PercentCompleted) * this.TaskInfo.Duration * this.Chart.hourInPixelsWork) / 100 + "px";
        imgPrF.style.height = this.Chart.heightTaskItem + "px";
        cellTblTask.appendChild(imgPrF);
        imgPrF.src = this.Chart.imgs + "progress_bg.png";

    }

    if (this.Chart.isEditable)
    {
        var divTaskInfo = document.createElement("div");
        divTaskInfo.style.cssText = "text-align:center;font-size:9px;z-index:2;position: absolute;left:0px;top:0px;";

        var tblTaskInfo = document.createElement("table");
        divTaskInfo.appendChild(tblTaskInfo);
        tblTaskInfo.cellPadding = "0";
        tblTaskInfo.cellSpacing = "0";
        tblTaskInfo.height = this.Chart.heightTaskItem + "px";
        tblTaskInfo.width = this.TaskInfo.Duration * this.Chart.hourInPixelsWork + "px";

        var rowTaskInfo = tblTaskInfo.insertRow(0);
        var cellTaskInfo = document.createElement("TD");
        cellTaskInfo.align = "center";
        cellTaskInfo.vAlign = "top";
        cellTaskInfo.height = this.Chart.heightTaskItem + "px";
        cellTaskInfo.className = "moveInfo";
        cellTaskInfo.style.cssText = ";white-space:nowrap;font-size:9px";
        rowTaskInfo.appendChild(cellTaskInfo);
        itemControl.appendChild(divTaskInfo);
    }

    var divTaskName = document.createElement("div");
    itemControl.appendChild(divTaskName);
    divTaskName.style.cssText = ";z-index:2;position: absolute;left:0px;top:0px;";

    var divMove = document.createElement("div");
    divMove.innerHTML = "<input type='text' style='visibility:hidden;width:1px;height:1px;'/>";
    if (this.Chart._isIE)
    {
        divMove.style.background = "#000000";
        divMove.style.filter = "alpha(opacity=0)";
    }
    divMove.style.height = this.Chart.heightTaskItem + "px";
    divMove.style.width = this.TaskInfo.Duration * this.Chart.hourInPixelsWork + "px";
    divTaskName.appendChild(divMove);

    if (this.Chart._showTooltip)
    {
        var getPopUpInfo = function(e) {
            if ((!self.Chart._isMove) && (!self.Chart._isResize)) self.getPopUpInfo(self.cTaskItem[0], e);
        };
        var closePopUpInfo = function() {
            self.closePopUpInfo();
        };

        this.addEvent(divMove, 'mouseover', getPopUpInfo, false);
        this.addEvent(divMove, 'mouseout', closePopUpInfo, false);
    }

    var taskClick = function() {
        self.Chart.callEvent("onTaskClick", [self]);
    };
    this.addEvent(divMove, 'click', taskClick, false);

    if (this.Chart.isEditable)
    {
        //Create resize area
        var divResize = document.createElement("div");
        divResize.style.cssText = ";z-index:10;position: absolute;left:" + (this.TaskInfo.Duration * this.Chart.hourInPixelsWork - 10) + "px;top:0px;";
        divResize.style.height = this.Chart.heightTaskItem + "px";
        divResize.style.width = "10px";
        divResize.innerHTML = "<input type='text' style='visibility:hidden;width:1px;height:1px;'/>";
        divTaskName.appendChild(divResize);

        var startMove = function(e) {
            if (self.Chart.callEvent("onTaskStartDrag", [self])===false) return;

            var moveItem = function(e1) {
                if (self.checkMove) self.moveItem(e1);
            };
            var endMove = function() {
                if (self.checkMove) {
                    self.endMove();
                    self.Chart._isMove = false;
                    if (self.Chart._isIE)
                    {
                        document.body.releaseCapture();
                        document.detachEvent("onmousemove", moveItem);
                        document.detachEvent("onmouseup", endMove);
                    } else {
                        document.removeEventListener("mousemove", moveItem, true);
                        document.removeEventListener("mouseup", endMove, true);
                    }
                    if (self.wasMoved) self.Chart.callEvent("onTaskEndDrag", [self]);
                }
            };
            self.addEvent(document, 'mousemove', moveItem, true);
            self.addEvent(document, 'mouseup', endMove, true);

            if (self.Chart._showTooltip) self.closePopUpInfo();
            self.startMove(e);
            self.Chart._isMove = true;
            if (self.Chart._isIE) document.body.setCapture(false);
        };

        var startResize = function(e) {
            if (self.Chart.callEvent("onTaskStartResize", [self])===false) return;

            var resizeItem = function(e1) {
                if (self.checkResize)self.resizeItem(e1);
            };

            var endResizeItem = function() {
                if (self.checkResize) {
                    self.endResizeItem();
                    self.Chart._isResize = false;
                    if (self.Chart._isIE)
                    {
                        document.body.releaseCapture();
                        document.detachEvent("onmousemove", resizeItem);
                        document.detachEvent("onmouseup", endResizeItem);
                    } else {
                        document.removeEventListener("mousemove", resizeItem, true);
                        document.removeEventListener("mouseup", endResizeItem, true);
                    }
                    if (self.wasResized) self.Chart.callEvent("onTaskEndResize", [self]);
                }
            };

            self.addEvent(document, 'mousemove', resizeItem, false);
            self.addEvent(document, 'mouseup', endResizeItem, false);

            self.startResize(e);
            if (self.Chart._isIE) document.body.setCapture(false);
            self.Chart._isResize = true;
        };

        this.addEvent(divMove, 'mousedown', startMove, false);
        this.addEvent(divResize, 'mousedown', startResize, false);

        var setCursorResize = function(e2) {
            if (!self.Chart._isMove) (e2.srcElement?e2.srcElement:e2.target).style.cursor = "e-resize";
        };
        var setCursorStandart = function(e3) {
            if (!self.checkResize) (e3.srcElement?e3.srcElement:e3.target).style.cursor = "";
        };

        this.addEvent(divResize, 'mouseover', setCursorResize, false);
        this.addEvent(divResize, 'mouseout', setCursorStandart, false);
    }
    return itemControl;
};
/**
 * @desc: creation of taskNameItem
 * @type: private
 * @topic: 0
 */
GanttTask.prototype.createTaskNameItem = function(hasChildren)
{
    var self = this;
    var divName = document.createElement("div");
    divName.id = this.TaskInfo.Id;
    divName.style.cssText = "cursor:pointer;white-space:nowrap;height:15px;z-index:1;position:absolute;left:20px;top: " + this.posY + "px;";
    if (hasChildren) divName.style.fontWeight = "bold";
    divName.className = "taskNameItem";
    divName.title = this.TaskInfo.Name;
    divName.innerHTML = this.TaskInfo.Name;
    if (this.Chart.isShowConMenu)
    {
        var showContMenu = function(event) {

            if (self.Chart.contextMenu.clear) self.Chart.contextMenu.clear();

            var hideContMenu = function() {
                self.Chart.contextMenu.hideContextMenu();
                if (self.Chart._isIE)
                    self.Chart.content.detachEvent("mousedown", hideContMenu);
                else
                    self.Chart.content.removeEventListener("mousedown", hideContMenu, false);
            };

            self.Chart.content.onmousedown = hideContMenu;

            if (!self.Chart._isIE)
            {
                event.stopPropagation();
            } else
            {
                event.cancelBubble = true;
            }

            self.Chart._showContextMenu(event, self);

        };

        if (this.Chart._isIE)
        {
            this.addEvent(divName, "contextmenu", function(e) {
                showContMenu(e);
                return false;
            }, false);

        } else
        {
            this.addEvent(divName, "contextmenu", function(e) {
                e.preventDefault();
                showContMenu(e);
            }, false);
        }
    }
    return divName;
};


GanttTask.prototype.createTaskDescItem = function()
{
    var posX = (this.posX + this.TaskInfo.Duration * this.Chart.hourInPixelsWork + 10);
    var divDesc = document.createElement("div");
    divDesc.style.cssText += ";z-index:1;position:absolute;left:" + posX + "px;top:" + this.posY + "px;";
    divDesc.innerHTML = this.getDescStr();
    divDesc.className = "descTask";
    this.descrTask = divDesc;

    if (this.Chart._showTooltip)
    {
        var self = this;
        var getPopUpInfo = function(e) {
            if ((!self.Chart._isMove) && (!self.Chart._isResize)) self.getPopUpInfo(self.descrTask, e);
        };
        var closePopUpInfo = function() {
            self.closePopUpInfo();
        };

        this.addEvent(divDesc, 'mouseover', getPopUpInfo, false);
        this.addEvent(divDesc, 'mouseout', closePopUpInfo, false);
    }
    return  divDesc;
};

/**
 * @desc: check Width of taskNameItem
 * @type: private
 * @topic: 4
 */
GanttTask.prototype.checkWidthTaskNameItem = function()
{
    if (this.cTaskNameItem[0].offsetWidth + this.cTaskNameItem[0].offsetLeft > this.Chart.maxWidthPanelNames)
    {
        var width = this.cTaskNameItem[0].offsetWidth + this.cTaskNameItem[0].offsetLeft - this.Chart.maxWidthPanelNames;
        var countChar = Math.round(width / (this.cTaskNameItem[0].offsetWidth / this.cTaskNameItem[0].firstChild.length));
        var tName = this.TaskInfo.Name.substring(0, this.cTaskNameItem[0].firstChild.length - countChar - 3);
        tName += "...";
        this.cTaskNameItem[0].innerHTML = tName;
    }

};
/**
 * @desc: creation of GanttTask
 * @type: private
 * @topic: 0
 */
GanttTask.prototype.create = function()
{
    var containerTasks = this.Chart.oData.firstChild;
    var containerNames = null;
    if (this.Chart._showTreePanel) containerNames = this.Chart.panelNames.firstChild;
    var predecessorTask = this.TaskInfo.PredecessorTask;
    var parentTask = this.TaskInfo.ParentTask;
    var isCParentTask = (this.TaskInfo.ChildTasks.length > 0);
    var self = this;

    this.cTaskItem = [];
    this.cTaskNameItem = [];

    //creation arrTasks
    if (!parentTask)
    {
        if (this.TaskInfo.previousParentTask) {
            this.previousParentTask = this.Project.getTaskById(this.TaskInfo.previousParentTask.Id);
            var lastChildTask = this.Chart.getLastChildTask(this.previousParentTask);
            this.posY = parseInt(lastChildTask.cTaskItem[0].style.top) + this.Chart.heightTaskItem + 11;
            this.previousParentTask.nextParentTask = this;

        } else {
            this.posY = parseInt(this.Project.projectItem[0].style.top) + this.Chart.heightTaskItem + 11;
        }
    }

    if (parentTask) {
        var task = this.Project.getTaskById(this.TaskInfo.ParentTask.Id);
        this.parentTask = task;

        if (this.TaskInfo.previousChildTask) {
            this.previousChildTask = this.Project.getTaskById(this.TaskInfo.previousChildTask.Id);
            var lastChildTask = this.Chart.getLastChildTask(this.previousChildTask);
            this.posY = parseInt(lastChildTask.cTaskItem[0].style.top) + this.Chart.heightTaskItem + 11;
            this.previousChildTask.nextChildTask = this;

        } else {
            this.posY = parseInt(task.cTaskItem[0].style.top) + this.Chart.heightTaskItem + 11;
        }
        task.childTask.push(this);
    }

    if (predecessorTask) {
        var task = this.Project.getTaskById(predecessorTask.Id);
        this.predTask = task;
        task.childPredTask.push(this);
    }

    //creation task item
    this.cTaskItem.push(this.createTaskItem());
    containerTasks.appendChild(this.cTaskItem[0]);

    if (this.Chart.panelNames) {
        this.cTaskNameItem.push(this.createTaskNameItem(isCParentTask));
        this.Chart.panelNames.firstChild.appendChild(this.cTaskNameItem[0]);
    }

    if (this.Chart.isShowDescTask) {
        containerTasks.appendChild(this.createTaskDescItem());
    }

    //Create Connecting Lines
    var arrConnectingLines = [];
    if (predecessorTask) arrConnectingLines = this.createConnectingLinesDS();
    this.cTaskItem.push(arrConnectingLines);

    if (this.Chart.panelNames)
    {
        //Create Connecting Lines
        var arrConnectingLinesNames = [];
        if (parentTask)
        {
            this.cTaskNameItem[0].style.left = parseInt(this.parentTask.cTaskNameItem[0].style.left) + 15 + "px";
            arrConnectingLinesNames = this.createConnectingLinesPN();
        }
        this.checkWidthTaskNameItem();

        var treeImg = null;
        if (isCParentTask) treeImg = this.createTreeImg();

        this.cTaskNameItem.push(arrConnectingLinesNames);
        this.cTaskNameItem.push(treeImg);
    }
    this.addDayInPanelTime();
    return this;
};

/**
 * @desc: creation of image of node
 * @type: private
 * @topic: 4
 */
GanttTask.prototype.createTreeImg = function()
{
    var self = this;
    var treeImg = new Image();
    treeImg.src = this.Chart.imgs + "minus.gif";
    treeImg.id = this.TaskInfo.Id;

    treeImg.onclick = function()
    {
        if (self._isOpen)
        {
            this.src = self.Chart.imgs + "plus.gif";
            self._isOpen = false;
            self.hideChildTasks(self);
            self.shiftCurrentTasks(self, -self._heightHideTasks);
        }
        else
        {
            this.src = self.Chart.imgs + "minus.gif";
            self._isOpen = true;
            self.shiftCurrentTasks(self, self._heightHideTasks);
            self.showChildTasks(self, true);
            self._heightHideTasks = 0;
        }
    };

    this.Chart.panelNames.firstChild.appendChild(treeImg);
    treeImg.style.cssText = "cursor:pointer;left:" + (parseInt(this.cTaskNameItem[0].style.left) - 12) + "px;top:" + (parseInt(this.cTaskNameItem[0].style.top) + 3) + "px;z-index:12;position:absolute;";

    return treeImg;
};
/**
 * @desc: returns last child of GanttTask
 * @type: private
 * @topic: 2
 */
GanttChart.prototype.getLastChildTask = function(task)
{
    if (task.childTask.length > 0)
    {
        return this.getLastChildTask(task.childTask[task.childTask.length - 1]);

    } else
    {
        return  task;
    }

};
/**
 * @desc: dhtmlXMLSenderObject constructor
 * @type: public
 * @topic: 0
 */
dhtmlXMLSenderObject = function(ganttChart)
{
    this.xmlHttp = this.createXMLHttpRequest();
    this.isProcessed = false;
    this.path = null;
    this.filename = null;
    this.Chart = ganttChart;
};
/**
 * @desc: creation (object) XMLHttpRequest
 * @type: private
 * @topic: 4
 */
dhtmlXMLSenderObject.prototype.createXMLHttpRequest = function()
{
    if (window.XMLHttpRequest) {
        return new XMLHttpRequest();
    }
    else if (window.ActiveXObject) {
        return new ActiveXObject("Microsoft.XMLHTTP");
    }
};
/**
 * @desc: Sends the data on a server
 * @type: private
 * @topic: 6
 */
dhtmlXMLSenderObject.prototype.sendData = function(filename, path, xmlData)
{
    var self = this;
    this.path = path;
    this.filename = filename;

    if ((this.path == null) || (this.path == ""))
    {
        this.Chart.Error.throwError("DATA_SEND_ERROR", 3, null);
        return;
    }
    if ((this.filename == null) || (this.filename == ""))
    {
        this.Chart.Error.throwError("DATA_SEND_ERROR", 4, null);
        return;
    }

    this.isProcessed = true;
    this.xmlHttp.open("POST", this.path, true);
    if (this.Chart._isFF)
    {
        this.xmlHttp.onerror = function() {
            self.xmlHttp.onreadystatechange = null;
            self.xmlHttp.abort();
            self.isProcessed = false;
        }
    }
    this.xmlHttp.onreadystatechange = function() {
        self.getStatus();
    };
    this.xmlHttp.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
    this.xmlHttp.send("data=" + encodeURI(xmlData) + "&filename=" + filename);


};
/**
 * @desc: Returns the status of operation
 * @type: private
 * @topic: 4
 */
dhtmlXMLSenderObject.prototype.getStatus = function()
{
    if (this.xmlHttp.readyState == 4)
    {

        var _status = "";
        try {
            _status = this.xmlHttp.status;

        } catch(e) {
            this.Chart.Error.throwError("DATA_SEND_ERROR", 1, null);
            return 0;
        }

        switch (_status) {

            case 0:
                this.Chart.Error.throwError("DATA_SEND_ERROR", 1, null);
                //this.xmlHttp.abort();
                break;
            case 404:
                this.Chart.Error.throwError("DATA_SEND_ERROR", 5, [this.path]);
                //this.xmlHttp.abort();
                break;
            case 500:
                this.Chart.Error.throwError("DATA_SEND_ERROR", 2, null);
                //this.xmlHttp.abort();
                break;
            case 12029:
                this.Chart.Error.throwError("DATA_SEND_ERROR", 1, null);
                //this.xmlHttp.abort();
                break;
            default:
                if (!(_status >= 200 && _status < 300 || _status == 304))
                {
                    this.Chart.Error.throwError("DATA_SEND_ERROR", 0, null);
                    //this.xmlHttp.abort();
                }
                break;
        }
        this.isProcessed = false;

    }
};
/**
 * @desc: GanttError constructor
 * @type: private
 * @topic: 0
 */
function GanttError() {

    this.catches = [];
    this._errors = [];
    this._init();

    return this;
}
/**
 *  @desc: initialization of control errors
 *  @type: private
 *  @topic: 4
 */
GanttError.prototype._init = function()
{
    //connection errors
    this._errors[0] = "Connection error";
    this._errors[1] = "Cannot connect";
    this._errors[2] = "Server error";
    this._errors[3] = "Path is null or empty";
    this._errors[4] = "Filename is null or empty";
    this._errors[5] = "File (%0) is not found";

    //API errors
    this._errors[6] = "Percent Complete  should be a number";
    this._errors[7] = "Percent Complete should be <= 100";
    this._errors[8] = "Percent Complete should be >= 0";
    this._errors[9] = "Increase duration of task(%0)";
    this._errors[10] = "Reduce duration of task(%0)";
    this._errors[11] = "Increase  EST of child task (%0)";
    this._errors[12] = "Reduce EST of task (%0)";
    this._errors[13] = "The project (%0) is added";
    this._errors[14] = "Start Date of the project < start Date of the control";
    this._errors[15] = "Task (%0) cannot be the child of predecessor task(%1)";
    this._errors[16] = "Time of the termination of predecessor task(%0) > EST of child task(%1)";
    this._errors[17] = "The Predecessor (%0) task  does not exist";
    this._errors[18] = "The EST of task (%0) < start date of the control";
    this._errors[19] = "Time of the termination of parent task (%0) < time of the termination of child task(%1)";
    this._errors[20] = "The EST of task (%0) < EST of parent task(%1)";
    this._errors[21] = "The parent task (%0) does not exist";
    this._errors[22] = "The task (%0) is added";
    this._errors[23] = "The project (%0) is added";
    this._errors[24] = "Task (%0) EST < project (%1) startDate";
    this._errors[25] = "Parent task (%0) EST cannot be null";
    this._errors[26] = "Predecessor task (%0) position error. Reduce duration of predecessor task (%0) or increase EST of child task (%1)";
    this._errors[27] = "Predecessor task (%0) does not exist";
    this._errors[28] = "Increase duration of parent task (%0) or reduce EST of child task (%1) or reduce duration of child task(%1)";
    this._errors[29] = "Reduce EST of parent task (%0) or increase  EST of child task (%1)";
    this._errors[30] = "The  task(%0) does not exist";
    this._errors[31] = "The project(%0) does not exist";
    this._errors[32] = "Predecessor task(%0) and child task(%1) should have the same parent";
    this._errors[33] = "Reduce EST of parent task (%0) or increase  EST of child task (%1)";
    this._errors[34] = "EST of task(%0) < start date of the project(%1)";
    this._errors[35] = "Percent Complete should be <= 100 and >= 0";
    this._errors[36] = "You may not connect a task to itself.";
    this._errors[37] = "Cannot parse this XML string.";
};
/**
 * @desc: bind type of exception with handler
 * @param: type - type of error
 * @param: handler - handler name
 * @type: private
 * @topic: 4
 */
GanttError.prototype.catchError = function(type, handler) {

    this.catches[type] = handler;
};
/**
 * @desc: get error string
 * @param: str - error message
 * @param: params - replace %i params in message
 * @type: private
 * @topic: 4
 */
GanttError.prototype.getErrorString = function(str, params)
{
    if (!params) {
        return str;
    } else {
        for (var i = 0; i < params.length; i++) {

            var re = new RegExp("%" + i, "gi");
            str = str.replace(re, params[i]);

        }
        return str;
    }
};
/**
 * @desc: throw error
 * @param: type - type of error
 * @param: description -  description of error
 * @param: params - current data
 * @type: private
 * @topic: 4
 */
GanttError.prototype.throwError = function(type, description, params) {
    if (this.catches[type])
    {
        var index = parseInt(description);
        var errorStr = this.getErrorString(this._errors[index], params);
        return  this.catches[type](type, errorStr, params);
    }
    return null;
};

function contextMenu(chart)
{
    this.Chart = chart;
    this.TabContainer = null;
    this.MenuPanel = null;
    this.tabPanel = null;
    this.arrTabs = [];
    this.isShow = false;
    this.hideDiv = null;
    this._init();
}

contextMenu.prototype._init = function()
{
    this.createMenuPanel();
    this.createHideDiv();
    this.createTabContainer();
    this.createTabPanel();

    var self = this;
    var arrItems = [];

    var tab1 = this.createTab(1, "Rename task", "t", true, this);
    tab1.addItem(1, "New name", document.createElement("input"), "text", function() {
        tab1.arrItems[0].control.focus();
    });
    tab1.addItem(2, "Rename", document.createElement("input"), "button",
            function() {
                var name = tab1.arrItems[0].control.value;
                try {
                    tab1.object.setName(name);
                    tab1.hide();
                } catch(e) {

                }
            }
            );

    var tab2 = this.createTab(2, "Delete task", "t", true, this);
    tab2.addItem(1, "Delete", document.createElement("input"), "button",
            function()
            {
                try {
                    tab2.object.Project.deleteTask(tab2.object.TaskInfo.Id);
                    tab2.hide();
                }
                catch(e) {

                }
            }
            );
    var tab3 = this.createTab(3, "Set EST", "t", true, this);
    tab3.addItem(1, "EST", document.createElement("input"), "text", function() {
        tab3.arrItems[0].control.focus();
    });
    tab3.addItem(2, "Move children", document.createElement("input"), "checkbox", function() {
        tab3.arrItems[1].control.focus();
    });
    tab3.addItem(3, "Update", document.createElement("input"), "button",
            function() {
                var isMoveChild = tab3.arrItems[1].control.checked;
                var arr = tab3.arrItems[0].control.value.split(".");
                var est = (arr.length < 3) ? null : (new Date(arr[2], parseInt(arr[1]) - 1, arr[0]));
                try {
                    if (tab3.object.setEST(est, isMoveChild)) tab3.hide();
                } catch(e) {

                }
            }
            );

    var tab4 = this.createTab(4, "Set duration", "t", true, this);
    tab4.addItem(1, "Duration", document.createElement("input"), "text", function() {
        tab4.arrItems[0].control.focus();
    });
    tab4.addItem(2, "Update", document.createElement("input"), "button",
            function() {
                var d = tab4.arrItems[0].control.value;
                try {
                    if (tab4.object.setDuration(d)) tab4.hide();
                } catch(e) {

                }
            }
            );

    var tab5 = this.createTab(5, "Set % complete", "t", true, this);
    tab5.addItem(1, "Percent Complete", document.createElement("input"), "text", function() {
        tab5.arrItems[0].control.focus();
    });
    tab5.addItem(2, "Update", document.createElement("input"), "button",
            function() {
                var p = tab5.arrItems[0].control.value;
                try {
                    if (tab5.object.setPercentCompleted(p)) tab5.hide();
                } catch(e) {

                }
            }
            );

    var tab13 = this.createTab(13, "Set predecessor", "t", true, this);
    tab13.addItem(1, "Predecessor", document.createElement("input"), "text", function() {
        tab13.arrItems[0].control.focus();
    });
    tab13.addItem(2, "Update", document.createElement("input"), "button",
            function() {
                var p = tab13.arrItems[0].control.value;
                try {
                    if (tab13.object.setPredecessor(p)) tab13.hide();
                } catch(e) {

                }
            }
            );

    var tab6 = this.createTab(6, "Rename project", "p", true, this);
    tab6.addItem(1, "New name", document.createElement("input"), "text", function() {
        tab6.arrItems[0].control.focus();
    });
    tab6.addItem(2, "Rename", document.createElement("input"), "button",
            function() {
                var name = tab6.arrItems[0].control.value;
                try {
                    tab6.object.setName(name);
                    tab6.hide();
                } catch(e) {

                }
            }
            );

    var tab7 = this.createTab(7, "Delete project", "p", true, this);
    tab7.addItem(1, "Delete", document.createElement("input"), "button",
            function() {
                try {
                    tab7.object.Chart.deleteProject(tab7.object.Project.Id);
                    tab7.hide();
                } catch(e) {

                }
            }
            );

    var tab8 = this.createTab(8, "Set % complete", "p", true, this);
    tab8.addItem(1, "Percent Complete", document.createElement("input"), "text", function() {
        tab8.arrItems[0].control.focus();
    });
    tab8.addItem(2, "Update", document.createElement("input"), "button",
            function() {
                var p = tab8.arrItems[0].control.value;
                try {
                    if (tab8.object.setPercentCompleted(p)) tab8.hide();
                } catch(e) {

                }
            }
            );

    var tab9 = this.createTab(9, "Add new task", "p", true, this);
    tab9.addItem(1, "Id", document.createElement("input"), "text", function() {
        tab9.arrItems[0].control.focus();
    });
    tab9.addItem(2, "Name", document.createElement("input"), "text", function() {
        tab9.arrItems[1].control.focus();
    });
    tab9.addItem(3, "EST", document.createElement("input"), "text", function() {
        tab9.arrItems[2].control.focus();
    });
    tab9.addItem(4, "Duration", document.createElement("input"), "text", function() {
        tab9.arrItems[3].control.focus();
    });
    tab9.addItem(5, "Percent complete", document.createElement("input"), "text", function() {
        tab9.arrItems[4].control.focus();
    });
    tab9.addItem(6, "Parent task id", document.createElement("input"), "text", function() {
        tab9.arrItems[5].control.focus();
    });
    tab9.addItem(7, "Pred task id", document.createElement("input"), "text", function() {
        tab9.arrItems[6].control.focus();
    });

    tab9.addItem(9, "Insert", document.createElement("input"), "button",
            function() {
                try {
                    var id = tab9.arrItems[0].control.value;
                    var name = tab9.arrItems[1].control.value;
                    var arr = tab9.arrItems[2].control.value.split(".");
                    var est = (arr.length < 3) ? null : (new Date(arr[2], parseInt(arr[1]) - 1, arr[0]));
                    var duration = tab9.arrItems[3].control.value;
                    var pc = tab9.arrItems[4].control.value;
                    var parentTaskId = tab9.arrItems[5].control.value;
                    var predTaskId = tab9.arrItems[6].control.value;
                    if (tab9.object.insertTask(id, name, est, duration, pc, predTaskId, parentTaskId)) tab9.hide();

                } catch(e) {

                }
            }
            );

    var tab11 = this.createTab(11, "Add successor task", "t", true, this);
    tab11.addItem(1, "Id", document.createElement("input"), "text", function() {
        tab11.arrItems[0].control.focus();
    });
    tab11.addItem(2, "Name", document.createElement("input"), "text", function() {
        tab11.arrItems[1].control.focus();
    });
    tab11.addItem(3, "EST", document.createElement("input"), "text", function() {
        tab11.arrItems[2].control.focus();
    });
    tab11.addItem(4, "Duration", document.createElement("input"), "text", function() {
        tab11.arrItems[3].control.focus();
    });
    tab11.addItem(5, "Percent complete", document.createElement("input"), "text", function() {
        tab11.arrItems[4].control.focus();
    });
    tab11.addItem(6, "Insert", document.createElement("input"), "button",
            function() {
                try {
                    var pr = tab11.object.Project;
                    var id = tab11.arrItems[0].control.value;
                    var name = tab11.arrItems[1].control.value;
                    var arr = tab11.arrItems[2].control.value.split(".");
                    var est = (arr.length < 3) ? null : (new Date(arr[2], parseInt(arr[1]) - 1, arr[0]));
                    var duration = tab11.arrItems[3].control.value;
                    var pc = tab11.arrItems[4].control.value;
                    var parentTaskId = (tab11.object.parentTask == null) ? "" : tab11.object.parentTask.TaskInfo.Id;
                    var predTaskId = tab11.object.TaskInfo.Id;
                    if (pr.insertTask(id, name, est, duration, pc, predTaskId, parentTaskId)) tab11.hide();

                } catch(e) {
                    //
                }
            }
            );

    var tab10 = this.createTab(10, "Add child task", "t", true, this);
    tab10.addItem(1, "Id", document.createElement("input"), "text", function() {
        tab10.arrItems[0].control.focus();
    });
    tab10.addItem(2, "Name", document.createElement("input"), "text", function() {
        tab10.arrItems[1].control.focus();
    });
    tab10.addItem(3, "EST", document.createElement("input"), "text", function() {
        tab10.arrItems[2].control.focus();
    });
    tab10.addItem(4, "Duration", document.createElement("input"), "text", function() {
        tab10.arrItems[3].control.focus();
    });
    tab10.addItem(5, "Percent complete", document.createElement("input"), "text", function() {
        tab10.arrItems[4].control.focus();
    });
    tab10.addItem(6, "Insert", document.createElement("input"), "button",
            function() {
                try {
                    var pr = tab10.object.Project;
                    var id = tab10.arrItems[0].control.value;
                    var name = tab10.arrItems[1].control.value;
                    var arr = tab10.arrItems[2].control.value.split(".");
                    var est = (arr.length < 3) ? null : (new Date(arr[2], parseInt(arr[1]) - 1, arr[0]));
                    var duration = tab10.arrItems[3].control.value;
                    var pc = tab10.arrItems[4].control.value;
                    var parentTaskId = tab10.object.TaskInfo.Id;
                    var predTaskId = "";
                    if (pr.insertTask(id, name, est, duration, pc, predTaskId, parentTaskId)) tab10.hide();

                } catch(e) {
                    //
                }
            }
            );

    var tab12 = this.createTab(12, "-Insert new project-", "p", false, this);
    tab12.addItem(1, "Id", document.createElement("input"), "text", function() {
        tab12.arrItems[0].control.focus();
    });
    tab12.addItem(2, "Name", document.createElement("input"), "text", function() {
        tab12.arrItems[1].control.focus();
    });
    tab12.addItem(3, "Start date", document.createElement("input"), "text", function() {
        tab12.arrItems[2].control.focus();
    });
    tab12.addItem(4, "Insert", document.createElement("input"), "button",
            function() {
                try {

                    var id = tab12.arrItems[0].control.value;
                    var namePr = tab12.arrItems[1].control.value;
                    var arr = tab12.arrItems[2].control.value.split(".");
                    var startDatePr = (arr.length < 3) ? null : (new Date(arr[2], parseInt(arr[1]) - 1, arr[0]));
                    if (self.Chart.insertProject(id, namePr, startDatePr)) tab12.hide();

                } catch(e) {

                }
            }
            );
};

contextMenu.prototype.createHideDiv = function()
{
    this.hideDiv = document.createElement("div");
    this.hideDiv.style.position = "absolute";
    this.hideDiv.style.left = "0px";
    this.hideDiv.style.top = "0px";
    this.Chart.content.appendChild(this.hideDiv);
    this.hideDiv.style.zIndex = 12;
    this.hideDiv.style.display = "none";
    this.hideDiv.style.background = "#7D7E7D";
    this.hideDiv.style.cssText += ";-moz-opacity: 0.5;filter: alpha(opacity=50);opacity:.50;";
    this.hideDiv.style.width = this.Chart.content.offsetWidth + 2 + "px";
    this.hideDiv.style.height = this.Chart.content.offsetHeight + 2 + "px";

};

contextMenu.prototype.createMenuPanel = function()
{
    this.MenuPanel = document.createElement("div");
    this.MenuPanel.style.visibility = "hidden";
    this.MenuPanel.style.cssText += ";z-index:10;";
    this.MenuPanel.style.position = "absolute";
    this.Chart.content.appendChild(this.MenuPanel);
    this.MenuPanel.innerHTML = "<table></table>";
    this.MenuPanel.firstChild.className = "contextMenu";

    this.MenuPanel.firstChild.cellPadding = 0;
    this.MenuPanel.firstChild.cellSpacing = 0;
    this.MenuPanel.firstChild.style.cssText += ";background:url(" + this.Chart.imgs + "menu/menu_bg.png);";
};
contextMenu.prototype.createTabPanel = function()
{
    this.tabPanel = document.createElement("div");
    this.tabPanel.style.visibility = "hidden";
    this.tabPanel.style.zIndex = "30";
    this.TabContainer.firstChild.rows[0].cells[0].appendChild(this.tabPanel);
    this.tabPanel.style.width = "385px";
    this.tabPanel.style.height = "290px";
    this.tabPanel.innerHTML = "<table><tr><td></td></tr><tr><td></td></tr></table>";
    this.tabPanel.firstChild.cellPadding = 0;
    this.tabPanel.firstChild.cellSpacing = 0;
    this.tabPanel.firstChild.style.cssText = "width:385px;border: 1px solid #808080;";
    this.tabPanel.firstChild.rows[0].cells[0].style.cssText = ";height:26px;background:url(" + this.Chart.imgs + "/menu/window_tr.png);background-repeat: no-repeat;color:#fff;font-size:14px;font-weight: bold;font-family: Tahoma, Arial";
    this.tabPanel.firstChild.rows[0].cells[0].align = "center";
    this.tabPanel.firstChild.rows[1].cells[0].style.cssText = ";height:270px;background:#F7F7F7;";
    this.tabPanel.firstChild.rows[1].cells[0].innerHTML = "<table></table>";
    this.tabPanel.firstChild.rows[1].cells[0].firstChild.style.cssText = "width:250px;font-size:11px;font-family:Tahoma,Arial;";
    this.tabPanel.firstChild.rows[1].cells[0].align = "center";
};

contextMenu.prototype.addItemMenuPanel = function(tab)
{
    var self = this;
    var row = this.MenuPanel.firstChild.insertRow(this.MenuPanel.firstChild.rows.length);
    var cell = document.createElement('td');
    cell.innerHTML = tab.Description;
    cell.style.cssText = "padding-left:10px;height:18px;";

    this.addEvent(cell, "mousedown", function() {
        tab.show();
    }, false);


    cell.onmouseover = function() {
        this.style.background = "url(" + self.Chart.imgs + "menu/menu_selection.png)";
    };
    cell.onmouseout = function() {
        this.style.background = "";
    };

    row.appendChild(cell);
};

contextMenu.prototype.showContextMenu = function(x, y, object)
{
    if (object.constructor == GanttTask)
    {
        for (var i = 0; i < this.arrTabs.length; i++) {
            if (this.arrTabs[i].type == "t")
            {
                this.arrTabs[i].object = object;
                this.addItemMenuPanel(this.arrTabs[i]);
            }
        }
    } else if (object.constructor == GanttProject)
    {
        for (var i = 0; i < this.arrTabs.length; i++) {
            if (this.arrTabs[i].type == "p")
            {
                this.arrTabs[i].object = object;
                this.addItemMenuPanel(this.arrTabs[i]);
            }
        }
    }

    this.isShow = true;
    this.MenuPanel.style.cssText += ";z-index:15;";
    this.MenuPanel.style.visibility = "visible";

    this.MenuPanel.style.top = parseInt(y) + this.Chart.heightTaskItem - this.Chart.oData.scrollTop + 5 + "px";
    this.MenuPanel.style.left = x;

};
contextMenu.prototype.hideContextMenu = function()
{
    this.isShow = false;
    this.MenuPanel.style.visibility = "hidden";

};
contextMenu.prototype.clear = function()
{
    this.MenuPanel.removeChild(this.MenuPanel.firstChild);
    this.MenuPanel.innerHTML = "<table></table>";
    this.MenuPanel.firstChild.className = "contextMenu";
    this.MenuPanel.firstChild.cellPadding = 0;
    this.MenuPanel.firstChild.cellSpacing = 0;
    this.MenuPanel.firstChild.style.cssText += ";background:url(" + this.Chart.imgs + "menu/menu_bg.png);";
};
contextMenu.prototype.createTab = function(id, desc, type, showOInfo, menu)
{
    var tab = new contextMenuTab(id, desc, type, showOInfo, menu);
    this.arrTabs.push(tab);
    return tab;
};
contextMenu.prototype.createTabContainer = function()
{
    this.TabContainer = document.createElement("div");
    this.TabContainer.style.position = "absolute";
    this.TabContainer.style.top = "0px";
    this.TabContainer.style.left = "0px";
    this.TabContainer.style.visibility = "hidden";
    this.TabContainer.style.zIndex = "50";
    this.Chart.content.appendChild(this.TabContainer);
    this.TabContainer.innerHTML = "<table><tr><td></td></tr></table>";
    this.TabContainer.firstChild.style.cssText = ";width:100%;height:100%;";
    this.TabContainer.firstChild.rows[0].cells[0].align = "center";
    this.TabContainer.style.width = this.Chart.content.offsetWidth + 2 + "px";
    this.TabContainer.style.height = this.Chart.content.offsetHeight + 2 + "px";

};

contextMenu.prototype.getTabById = function(id)
{
    for (var i = 0; i < this.arrTabs.length; i++) {
        if (this.arrTabs[i].Id == id) {
            return this.arrTabs[i];
        }
    }
    return null;
};
function contextMenuTab(id, description, type, showOInfo, contextMenu)
{
    this.Id = id;
    this.arrItems = [];
    this.TabItemContainer = null;
    this.Description = description;
    this.contextMenu = contextMenu;
    this.type = type;
    this.object = null;
    this.showObjectInfo = showOInfo;

}

/**
 * @desc: add event
 * @param: elm - current element
 * @param: evType - string that specifies any of the standard DHTML Events
 * @param: fn -  pointer that specifies the function to call when sEvent fires
 * @type:  private
 * @topic: 5
 */
contextMenu.prototype.addEvent = function (elm, evType, fn, useCapture)
{
    if (elm.addEventListener) {
        elm.addEventListener(evType, fn, useCapture);
        return true;
    }
    else if (elm.attachEvent) {
        return elm.attachEvent('on' + evType, fn);
    }
    else {
        elm['on' + evType] = fn;
    }
};

contextMenuTab.prototype.addItem = function(id, name, control, type, handler)
{
    if (handler) {
        control.onclick = handler;
    }
    control.type = type;
    if (type == "button")
    {
        control.value = name;
    }
    var tabItem = new contextMenuTabItem(id, name, control, this);
    this.arrItems.push(tabItem);
};

contextMenuTab.prototype.show = function()
{
    this.contextMenu.hideDiv.style.display = "inline";
    this.contextMenu.TabContainer.style.visibility = "visible";

    var self = this;
    this.contextMenu.tabPanel.firstChild.rows[0].cells[0].innerHTML = this.Description;
    this.contextMenu.tabPanel.style.visibility = "visible";
    var t = this.contextMenu.tabPanel.firstChild.rows[1].cells[0].firstChild;
    var c,c2,r = null;

    if (this.showObjectInfo)
    {
        if (this.object) {
            if (this.object.constructor == GanttTask) {
                this.insertData(t, "Id", this.object.TaskInfo.Id);
                this.insertData(t, "Name", this.object.TaskInfo.Name);
                this.insertData(t, "Duration", this.object.TaskInfo.Duration + " hrs");
                this.insertData(t, "Percent complete", this.object.TaskInfo.PercentCompleted + "%");
                this.insertData(t, "EST", this.object.TaskInfo.EST.getDate() + "." + (this.object.TaskInfo.EST.getMonth() + 1) + "." + this.object.TaskInfo.EST.getFullYear());
                this.insertData(t, "Predecessor", this.object.TaskInfo.PredecessorTaskId);
            } else
            {
                this.insertData(t, "Id", this.object.Project.Id);
                this.insertData(t, "Name", this.object.Project.Name);
                this.insertData(t, "Start date", this.object.Project.StartDate.getDate() + "." + (this.object.Project.StartDate.getMonth() + 1) + "." + this.object.Project.StartDate.getFullYear());
            }
        }
    }

    var btnCell = null;
    for (var i = 0; i < this.arrItems.length; i++) {
        if (this.arrItems[i].control.type == "button")
        {
            r = t.insertRow(t.rows.length);
            c = r.insertCell(r.cells.length);
            btnCell = r.insertCell(r.cells.length);
            btnCell.appendChild(this.arrItems[i].control);

        } else
        {
            r = t.insertRow(t.rows.length);
            c = r.insertCell(r.cells.length);
            c2 = r.insertCell(r.cells.length);
            c.innerHTML = this.arrItems[i].Name;
            c2.appendChild(this.arrItems[i].control);

        }
    }

    var b = document.createElement("input");
    b.type = "button";
    b.value = "Cancel";
    b.onclick = function()
    {
        self.hide();
    };

    if (!btnCell) {
        r = t.insertRow(t.rows.length);
        c = r.insertCell(r.cells.length);
        btnCell = r.insertCell(r.cells.length);
    } else {
        b.style.marginLeft = "10px";
    }
    btnCell.appendChild(b);
};
contextMenuTab.prototype.hide = function()
{
    this.contextMenu.tabPanel.style.visibility = "hidden";
    var t = this.contextMenu.tabPanel.firstChild.rows[1].cells[0].firstChild;
    t.parentNode.removeChild(t);
    this.contextMenu.tabPanel.firstChild.rows[1].cells[0].innerHTML = "<table></table>";
    this.contextMenu.tabPanel.firstChild.rows[1].cells[0].firstChild.style.cssText = "width:250px;font-size:11px;font-family:Tahoma,Arial;";

    this.contextMenu.hideDiv.style.display = "none";
    this.contextMenu.TabContainer.style.visibility = "hidden";
};

contextMenuTab.prototype.insertData = function(t, name, value)
{
    var c,c2,r = null;
    r = t.insertRow(t.rows.length);
    c = r.insertCell(r.cells.length);
    c.style.cssText = "width:100px";
    c.innerHTML = name;
    c2 = r.insertCell(r.cells.length);
    c2.innerHTML = value;

};
contextMenuTab.prototype.insertControl = function(t, name, value)
{
    var c,c2,r = null;
    r = t.insertRow(t.rows.length);
    c = r.insertCell(r.cells.length);
    c.innerHTML = name;
    c2 = r.insertCell(r.cells.length);
    c2.appendChild(value);
};

function contextMenuTabItem(id, name, control, tab)
{
    this.Id = id;
    this.Name = name;
    this.control = control;
    this.tab = tab;

}
