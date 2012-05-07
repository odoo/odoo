openerp.project_issue = function(openerp) {
    openerp.web_kanban.ProjectIssueKanban = openerp.web_kanban.KanbanRecord.include({
        bind_events: function() {
            self = this;
            self._super();
            if(this.view.dataset.model == 'project.project') {
	        if(this.record.use_tasks.raw_value && this.record.use_issues.raw_value)$(this.$element).find('.click_button').attr('data-name','open_tasks');
	        if(!this.record.use_tasks.raw_value && this.record.use_issues.raw_value)$(this.$element).find('.click_button').attr('data-name','open_issues');
            };
            	
        }
    });
}
