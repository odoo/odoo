odoo.define('project.ProjectUpdateComponent', (function(require) {

    const {Component} = owl;

    class ProjectUpdateComponent extends Component {
        constructor (parent, props){
            super(...arguments);

            this.res_id = props.res_id;
            this.status = 'test';
            this.name = 'test update name';
        }

        _updateStatus(model){
            this.status = model.status;
            this.name = model.name;
        }

        _onClickStatus(){
            this.do_action({
                type: 'ir.actions.act_window',
                views: [[false, 'form']],
                target: 'current',
                res_model: 'project.update',
                res_id: this.res_id
            });
        }
    }
    ProjectUpdateComponent.template = 'project.ProjectUpdateComponent';

    return ProjectUpdateComponent;
}));