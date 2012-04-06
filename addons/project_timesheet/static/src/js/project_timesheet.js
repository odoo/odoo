openerp.project_timesheet = function(openerp) {
    openerp.web_kanban.ProjectTimeSheetKanban = openerp.web_kanban.KanbanRecord.include({
        bind_events: function() {
            self = this;
            self._super();
            if(this.view.dataset.model == 'project.project') {
	            if(this.record.task.raw_value && this.record.issues.raw_value && this.record.timesheets.raw_value)$(this.$element).find('.click_button').attr('data-name','open_tasks');
	            if(!this.record.task.raw_value && !this.record.issues.raw_value && this.record.timesheets.raw_value)$(this.$element).find('.click_button').attr('data-name','open_timesheets');
	            //if(!this.record.task.raw_value)$(this.$element).find('.click_button').attr('data-name','dummy');
            };
        }
    });
}
